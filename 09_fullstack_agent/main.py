import json
import os
from agents import run_architect, run_coder_for_file, run_tester, run_readme_writer, validate_goal

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
STATE_FILE    = os.path.join(BASE_DIR, "project_db/state.json")
WORKSPACE     = os.path.join(BASE_DIR, "workspace")
CONTRACTS_DIR = os.path.join(BASE_DIR, "project_db/contracts")
API_SPEC      = os.path.join(CONTRACTS_DIR, "api_spec.md")
FILE_PLAN     = os.path.join(CONTRACTS_DIR, "file_plan.json")

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"goal": "", "architect_done": False, "files_done": []}

def save_state(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)

def sep(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
        print(f"{'='*60}")

def run_project(goal):
    os.makedirs(WORKSPACE, exist_ok=True)
    state = load_state()
    state["goal"] = goal
    save_state(state)

    sep(f"Goal: {goal}")

    # ── Phase 1: Architect ────────────────────────────────────────────────
    sep("Phase 1 / Architect → 生成接口契约 + 文件清单")
    # checkpoint 必须验证文件真实存在，否则重跑
    architect_ok = (
        state.get("architect_done")
        and os.path.exists(FILE_PLAN)
        and os.path.exists(API_SPEC)
    )
    if architect_ok:
        print("  ✓ 已完成（checkpoint）")
    else:
        state["architect_done"] = False   # 重置坏掉的 checkpoint
        os.makedirs(CONTRACTS_DIR, exist_ok=True)
        run_architect(goal, WORKSPACE, CONTRACTS_DIR)
        if os.path.exists(FILE_PLAN) and os.path.exists(API_SPEC):
            state["architect_done"] = True
            save_state(state)
            print("  ✓ 架构完成")
        else:
            print("  ✗ Architect 未能生成必要文件，请重试")
            return

    # 读取文件清单
    if not os.path.exists(FILE_PLAN):
        print("  ✗ file_plan.json 未生成，请检查 Architect 输出")
        return
    file_plan = json.load(open(FILE_PLAN))
    api_spec  = open(API_SPEC).read() if os.path.exists(API_SPEC) else ""

    sep(f"Phase 2 / Coder → 逐文件实现（共 {len(file_plan)} 个文件）")

    # ── Phase 2: 逐文件编写 ──────────────────────────────────────────────
    for i, file_info in enumerate(file_plan):
        path = file_info["path"]
        full_path = os.path.join(WORKSPACE, path)

        # Checkpoint：已完成的文件跳过
        if path in state.get("files_done", []):
            print(f"  [{i+1}/{len(file_plan)}] ✓ {path}（checkpoint）")
            continue

        print(f"\n  [{i+1}/{len(file_plan)}] 写入: {path}")
        print(f"          职责: {file_info['desc']}")

        run_coder_for_file(file_info, api_spec, WORKSPACE)

        # 验证文件确实被写入了
        if os.path.exists(full_path):
            lines = len(open(full_path, encoding="utf-8").readlines())
            print(f"          ✓ 写入成功 ({lines} 行)")
            state["files_done"].append(path)
            save_state(state)
        else:
            print(f"          ✗ 文件未生成！")

    # ── Phase 3: 验证 ────────────────────────────────────────────────────
    sep("Phase 3 / Tester → 验证后端启动 + 前端构建")
    test_report = run_tester(WORKSPACE)
    print(f"\n  测试报告:\n{test_report}")

    # ── Phase 4: README ──────────────────────────────────────────────────
    sep("Phase 4 / README Writer → 生成使用文档")
    readme_path = os.path.join(WORKSPACE, "README.md")
    if os.path.exists(readme_path):
        print("  ✓ 已完成（checkpoint）")
    else:
        run_readme_writer(WORKSPACE, CONTRACTS_DIR)
        if os.path.exists(readme_path):
            print(f"  ✓ README.md 已生成 → {readme_path}")
        else:
            print("  ✗ README.md 未生成")

    # ── Phase 5: Master 验收 ─────────────────────────────────────────────
    sep("Phase 5 / Master → Goal 验收")
    passed, verdict = validate_goal(goal, test_report)
    print(f"\n  {verdict}")
    print(f"\n{'🎉 Goal 达成！' if passed else '💥 需要人工介入'}")

if __name__ == "__main__":
    run_project(
        "一个 Todo 管理应用：FastAPI 后端提供 CRUD API，Vue3 前端展示和操作 Todo 列表"
    )
