#!/usr/bin/env python3
"""
my_claude_code - 你自己的 AI 编程助手
用法: python3 main.py
"""
import os
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

# ── 可用模型列表 ──────────────────────────────────────────────────────────
MODELS = {
    "deepseek-v4-pro":    "DeepSeek V4 Pro（默认，最强）",
    "deepseek-chat":      "DeepSeek Chat（快速）",
    "deepseek-reasoner":  "DeepSeek R1（慢但推理强）",
}

# prompt_toolkit 的颜色样式
STYLE = Style.from_dict({
    "prompt-you":   "#00aa00 bold",
    "prompt-model": "#888888",
    "prompt-sep":   "#444444",
})

HELP_TEXT = """
  内置命令：
  /help              显示帮助
  /clear             清空当前对话
  /history           显示对话轮数
  /model             查看当前模型
  /model <name>      切换模型
  /models            列出所有可用模型
  /cd <path>         切换工作目录
  /exit              退出
"""

def make_prompt(model_name):
    """生成带模型名的彩色提示符"""
    return HTML(f'<prompt-you>你</prompt-you> <prompt-model>[{model_name}]</prompt-model><prompt-sep> › </prompt-sep>')

def main():
    from agent import Agent

    current_model = "deepseek-v4-pro"
    agent = Agent(model=current_model)

    # PromptSession 解决中文输入问题：
    # - 正确处理 UTF-8 多字节字符
    # - 支持方向键历史翻页
    # - 支持 Ctrl+C 中断输入（不退出程序）
    session = PromptSession()

    print("\n\033[1m🤖 my_claude_code\033[0m")
    print(f"   模型: {current_model}  |  工作目录: {os.getcwd()}")
    print("   输入 /help 查看命令\n")

    while True:
        try:
            user_input = session.prompt(
                make_prompt(current_model),
                style=STYLE,
            ).strip()
        except KeyboardInterrupt:
            # Ctrl+C 只取消当前输入，不退出
            print()
            continue
        except EOFError:
            # Ctrl+D 退出
            print("\n再见！")
            break

        if not user_input:
            continue

        # ── 内置命令 ─────────────────────────────────────────────────────
        if user_input == "/exit":
            print("再见！")
            break

        elif user_input == "/help":
            print(HELP_TEXT)

        elif user_input == "/clear":
            agent.messages = []
            print("  ✓ 对话已清空\n")

        elif user_input == "/history":
            turns = len([m for m in agent.messages if m["role"] == "user"])
            print(f"  当前对话: {turns} 轮，共 {len(agent.messages)} 条消息\n")

        elif user_input == "/models":
            print("\n  可用模型:")
            for name, desc in MODELS.items():
                mark = " ◀ 当前" if name == current_model else ""
                print(f"    {name:<25} {desc}{mark}")
            print()

        elif user_input == "/model":
            print(f"  当前模型: {current_model}  ({MODELS.get(current_model, '未知')})\n")

        elif user_input.startswith("/model "):
            new_model = user_input[7:].strip()
            if new_model in MODELS:
                current_model = new_model
                agent.set_model(new_model)
                print(f"  ✓ 切换到: {current_model}\n")
            else:
                print(f"  ✗ 未知模型: {new_model}")
                print(f"  可用模型: {', '.join(MODELS.keys())}\n")

        elif user_input.startswith("/cd "):
            path = user_input[4:].strip()
            try:
                os.chdir(path)
                agent.update_cwd(os.getcwd())
                print(f"  ✓ 工作目录: {os.getcwd()}\n")
            except FileNotFoundError:
                print(f"  ✗ 目录不存在: {path}\n")

        # ── 正常对话 ──────────────────────────────────────────────────────
        else:
            print("\033[34mAI\033[0m  ", end="", flush=True)
            agent.run(user_input)
            print()

if __name__ == "__main__":
    main()
