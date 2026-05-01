import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from config import API_KEY, BASE_URL, MODEL
from tools import read_file, write_file, edit_file, list_tree, search_code
from tools import run_bash, is_dangerous
from tools import git_status, git_diff, git_log, git_commit

client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

TOOLS = [
    {"name": "read_file", "description": "读取文件内容（带行号）",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}}, "required": ["path"]}},

    {"name": "write_file", "description": "写入文件",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"}, "content": {"type": "string"}},
         "required": ["path", "content"]}},

    {"name": "edit_file", "description": "精确替换文件中某段内容",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string"},
         "old_str": {"type": "string"},
         "new_str": {"type": "string"}},
         "required": ["path", "old_str", "new_str"]}},

    {"name": "list_tree", "description": "查看目录结构",
     "input_schema": {"type": "object", "properties": {
         "path": {"type": "string", "default": "."}}}},

    {"name": "search_code", "description": "在代码中搜索关键词",
     "input_schema": {"type": "object", "properties": {
         "keyword": {"type": "string"},
         "path": {"type": "string", "default": "."}},
         "required": ["keyword"]}},

    {"name": "run_bash", "description": "执行 shell 命令",
     "input_schema": {"type": "object", "properties": {
         "command": {"type": "string"},
         "cwd": {"type": "string"}},
         "required": ["command"]}},

    {"name": "git_status", "description": "查看 git 状态",
     "input_schema": {"type": "object", "properties": {}}},

    {"name": "git_diff", "description": "查看文件改动",
     "input_schema": {"type": "object", "properties": {
         "file": {"type": "string"}}}},

    {"name": "git_commit", "description": "提交所有改动",
     "input_schema": {"type": "object", "properties": {
         "message": {"type": "string"}},
         "required": ["message"]}},
]

def dispatch(name, inputs):
    if name == "read_file":    return read_file(inputs["path"])
    if name == "write_file":   return write_file(inputs["path"], inputs["content"])
    if name == "edit_file":    return edit_file(inputs["path"], inputs["old_str"], inputs["new_str"])
    if name == "list_tree":    return list_tree(inputs.get("path", "."))
    if name == "search_code":  return search_code(inputs["keyword"], inputs.get("path", "."))
    if name == "git_status":   return git_status()
    if name == "git_diff":     return git_diff(inputs.get("file"))
    if name == "git_commit":   return git_commit(inputs["message"])
    if name == "run_bash":
        cmd = inputs["command"]
        # ── 权限系统：危险命令先问用户 ──────────────────────────────────
        if is_dangerous(cmd):
            print(f"\n  ⚠️  危险命令: {cmd}")
            confirm = input("  确认执行？(Y/N) ").strip().lower()
            if confirm != "Y":
                return "[用户取消] 命令未执行"
        return run_bash(cmd, inputs.get("cwd"))
    return f"[错误] 未知工具: {name}"


class Agent:
    def __init__(self, model=None):
        self.messages = []
        self.model = model or MODEL  # 动态可切换

        self.system = f"""你是一个 AI 编程助手，类似 Claude Code。
当前工作目录: {os.getcwd()}

你可以：
- 读写和修改代码文件
- 执行 shell 命令
- 搜索代码
- 操作 git

规则：
- 修改文件用 edit_file（精确替换），不要整个重写
- 执行命令前先解释你要做什么
- 报错时先读文件理解上下文再修复"""

    def set_model(self, model):
        """切换模型，保留对话历史"""
        self.model = model

    def update_cwd(self, cwd):
        """更新工作目录信息"""
        self.system = self.system.split("当前工作目录:")[0] + f"当前工作目录: {cwd}"

    def run(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(30):
            print("\n", end="", flush=True)
            full_text = ""

            with client.messages.stream(
                model=self.model,  # 使用当前选中的模型
                max_tokens=8192,
                system=self.system,
                tools=TOOLS,
                messages=self.messages
            ) as stream:
                for event in stream:
                    # 文字 token 实时打印
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            delta = event.delta
                            if hasattr(delta, "text"):
                                print(delta.text, end="", flush=True)
                                full_text += delta.text

            print()  # 换行

            # 获取完整响应
            response = stream.get_final_message()
            stop_reason = response.stop_reason

            if stop_reason == "end_turn":
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                break

            if stop_reason == "tool_use":
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"\n  \033[36m[{block.name}]\033[0m ", end="")
                        # 打印工具参数预览
                        first_val = list(block.input.values())[0] if block.input else ""
                        print(str(first_val)[:60].replace("\n", " "))

                        result = dispatch(block.name, block.input)

                        # 结果预览（太长就截断）
                        preview = str(result)[:200].replace("\n", " ")
                        print(f"  \033[90m→ {preview}\033[0m")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)
                        })
                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })
            else:
                break
