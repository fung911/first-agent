import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from config import API_KEY, BASE_URL, MODEL
from tools import dispatch

client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

# ── 工具 schema 定义 ──────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "read_file",
        "description": "读取文件内容（带行号）",
        "input_schema": {"type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]}
    },
    {
        "name": "write_file",
        "description": "写入文件（自动创建父目录）",
        "input_schema": {"type": "object",
            "properties": {
                "path":    {"type": "string"},
                "content": {"type": "string"}
            }, "required": ["path", "content"]}
    },
    {
        "name": "edit_file",
        "description": "精确替换文件中的某段内容",
        "input_schema": {"type": "object",
            "properties": {
                "path":    {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"}
            }, "required": ["path", "old_str", "new_str"]}
    },
    {
        "name": "mkdir",
        "description": "创建目录（含所有父目录）",
        "input_schema": {"type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]}
    },
    {
        "name": "list_tree",
        "description": "查看目录树结构（不显示文件内容）",
        "input_schema": {"type": "object",
            "properties": {"path": {"type": "string", "default": "."}},
            "required": []}
    },
    {
        "name": "run_bash",
        "description": "执行 shell 命令",
        "input_schema": {"type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd":     {"type": "string", "description": "执行目录（可选）"}
            }, "required": ["command"]}
    },
]

# ── 通用 agent 循环 ───────────────────────────────────────────────────────
def _run_agent(system, user, max_tokens=8192, max_iter=30, tools=None):
    if tools is None:
        tools = TOOLS
    messages = [{"role": "user", "content": user}]
    final_text = ""
    for _ in range(max_iter):
        resp = client.messages.create(
            model=MODEL, max_tokens=max_tokens,
            system=system, tools=tools, messages=messages
        )
        if resp.stop_reason == "end_turn":
            final_text = next((b.text for b in resp.content if b.type == "text"), "")
            break
        elif resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    result = dispatch(b.name, b.input)
                    # 打印工具调用（截断长输出）
                    first_input = list(b.input.values())[0] if b.input else ""
                    preview = str(first_input)[:50].replace('\n', ' ')
                    print(f"    [{b.name}] {preview}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": str(result)
                    })
            messages.append({"role": "user", "content": results})
        else:
            print(f"    [警告] stop_reason={resp.stop_reason}，终止")
            break
    return final_text

# ─────────────────────────────────────────────────────────────────────────
# Architect Agent
# 输出1：project_db/contracts/api_spec.md   → API 接口定义（前后端共同遵守）
# 输出2：project_db/contracts/file_plan.json → 所有文件清单+依赖关系
# ─────────────────────────────────────────────────────────────────────────
def run_architect(goal, workspace, contracts_dir):
    return _run_agent(
        system=f"""你是系统架构师，负责设计全栈项目的完整架构。

代码工作目录：{workspace}
契约输出目录：{contracts_dir}

你需要输出两个文件（使用绝对路径）：

**文件1：{contracts_dir}/api_spec.md**
内容：所有 API 接口的精确定义
- 每个接口的 Method、Path、Request Body、Response Body
- Pydantic 模型定义
- 前端调用示例

**文件2：{contracts_dir}/file_plan.json**
内容：JSON 数组，项目所有文件的清单
格式：
[
  {{
    "path": "相对于workspace的文件路径",
    "type": "backend|frontend|config",
    "desc": "这个文件的职责",
    "depends_on": ["依赖的其他文件路径列表，按需读取"]
  }}
]

要求：
- 文件要完整，不能遗漏任何必要文件
- depends_on 要准确，Coder 会按这个读取上下文
- 包含所有配置文件（requirements.txt、package.json、vite.config.js等）
- backend 用 FastAPI + uvicorn
- frontend 用 Vue3 + Vite（不用 TypeScript，用普通 JS）
- 前后端通过 REST API 通信
- 包含 CORS 配置
- file_plan.json 中 path 字段是相对于 {workspace} 的路径""",
        user=f"需求：{goal}\n\n请将两个文件写入绝对路径：\n- {contracts_dir}/api_spec.md\n- {contracts_dir}/file_plan.json",
        max_tokens=8192,
        tools=[t for t in TOOLS if t["name"] in ("write_file", "mkdir", "read_file")]
    )

# ─────────────────────────────────────────────────────────────────────────
# Coder Agent（逐文件）
# 每次只写一个文件，按 depends_on 读取必要上下文
# ─────────────────────────────────────────────────────────────────────────
def run_coder_for_file(file_info, api_spec, workspace):
    path = file_info["path"]
    desc = file_info["desc"]
    depends = file_info.get("depends_on", [])

    # 读取依赖文件内容，作为上下文
    dep_context = ""
    for dep in depends:
        full_dep = os.path.join(workspace, dep)
        if os.path.exists(full_dep):
            content = open(full_dep, encoding="utf-8").read()
            dep_context += f"\n\n--- {dep} ---\n{content}"

    return _run_agent(
        system=f"""你是资深全栈工程师。你的任务是写一个具体的文件。

API 接口契约（所有文件必须遵守）：
{api_spec}

规则：
- 严格按照接口契约实现，不要自创接口
- 代码要完整可运行，不能有省略号或 TODO
- 文件路径相对于工作目录 {workspace}
- Vue3 使用 Composition API (setup)
- FastAPI 要配置 CORS 允许所有来源（开发环境）""",
        user=f"""请写这个文件：

文件路径：{os.path.join(workspace, path)}
文件职责：{desc}

{"依赖文件内容（你需要参考这些）：" + dep_context if dep_context else "（无依赖文件）"}

请直接用 write_file 写入完整代码，不要省略任何部分。""",
        max_tokens=8192,
        tools=[t for t in TOOLS if t["name"] in ("write_file", "edit_file", "read_file", "mkdir")]
    )

# ─────────────────────────────────────────────────────────────────────────
# Tester Agent：验证后端能启动，前端能构建
# ─────────────────────────────────────────────────────────────────────────
def run_tester(workspace):
    return _run_agent(
        system=f"""你是 QA 工程师，验证全栈项目能正常启动。工作目录：{workspace}

验证步骤：
1. list_tree 查看项目结构是否完整
2. 后端验证：
   - run_bash: cd {workspace}/backend && pip install -r requirements.txt -q
   - run_bash: cd {workspace}/backend && python -c "from main import app; print('backend OK')"
3. 前端验证：
   - run_bash: cd {workspace}/frontend && npm install --silent 2>&1 | tail -3
   - run_bash: cd {workspace}/frontend && npm run build 2>&1 | tail -10
4. 报告哪些通过了，哪些失败了""",
        user="请按步骤验证项目，并给出最终报告。",
        max_tokens=4096
    )

# ─────────────────────────────────────────────────────────────────────────
# README Writer Agent
# 读取项目结构 + 契约，生成 README.md 到 workspace 根目录
# ─────────────────────────────────────────────────────────────────────────
def run_readme_writer(workspace, contracts_dir):
    return _run_agent(
        system=f"""你是技术文档工程师。根据项目结构和 API 契约，生成一份完整的 README.md。

README 必须包含：
# 项目名称 + 一句话描述

## 技术栈
- 后端：FastAPI + Python
- 前端：Vue3 + Vite

## 项目结构
（用目录树展示）

## 快速启动

### 后端
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

## API 文档
（列出所有接口：Method、Path、说明）

## 开发说明
（任何需要注意的事项）

写入路径：{workspace}/README.md""",
        user=f"""请：
1. list_tree("{workspace}") 查看项目结构
2. read_file("{contracts_dir}/api_spec.md") 获取 API 定义
3. 生成 README.md 写入 {workspace}/README.md""",
        max_tokens=4096,
        tools=[t for t in TOOLS if t["name"] in ("list_tree", "read_file", "write_file")]
    )

# ─────────────────────────────────────────────────────────────────────────
# Master Validation
# ─────────────────────────────────────────────────────────────────────────
def validate_goal(goal, test_report):
    resp = client.messages.create(
        model=MODEL, max_tokens=256,
        messages=[{"role": "user", "content": f"""
目标：{goal}
测试报告：{test_report}

后端和前端都能正常启动/构建吗？
只回答 PASS 或 FAIL，加一句原因。
"""}]
    )
    text = next((b.text for b in resp.content if b.type == "text"), "FAIL")
    return "PASS" in text.upper(), text
