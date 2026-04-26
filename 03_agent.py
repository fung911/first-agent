import anthropic
from config import API_KEY, BASE_URL, MODEL

client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

# ── 工具说明书（告诉 AI 有哪些工具）────────────────────────────────────────
tools = [
    {
        "name": "write_file",
        "description": "把内容写入一个文件",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "读取一个文件的内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "required": ["path"]
        }
    }
]

# ── 真正执行工具的函数（普通 Python 代码）────────────────────────────────────
def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"已成功写入 {path}"

def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"文件 {path} 不存在"

def execute_tool(name, inputs):
    print(f"  >>> 执行工具: {name}，参数: {inputs}")
    if name == "write_file":
        return write_file(inputs["path"], inputs["content"])
    if name == "read_file":
        return read_file(inputs["path"])
    return "未知工具"

# ── Agent 主循环 ──────────────────────────────────────────────────────────
def run_agent(user_input):
    print(f"\n用户: {user_input}")
    print("─" * 40)

    # messages 是整个对话历史，每一轮都追加进去
    messages = [
        {"role": "user", "content": user_input}
    ]

    # while loop：不断循环，直到 AI 说 end_turn（任务完成）
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        print(f"[stop_reason: {response.stop_reason}]")

        # ── 情况一：AI 说完了，任务结束 ──
        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    print(f"\nAI: {block.text}")
            break

        # ── 情况二：AI 要用工具 ──
        if response.stop_reason == "tool_use":
            # 第一步：把 AI 这轮的回复追加到对话历史
            # （必须做，否则 AI 下一轮不知道自己说过什么）
            messages.append({"role": "assistant", "content": response.content})

            # 第二步：找出所有工具调用，逐个执行，收集结果
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,  # ← 必须对应 AI 调用时的 id
                        "content": result
                    })

            # 第三步：把工具执行结果还给 AI，让它继续思考
            messages.append({"role": "user", "content": tool_results})

            # 回到 while 开头，AI 拿到结果后继续下一轮


# ── 测试 ──────────────────────────────────────────────────────────────────
run_agent("帮我把'我学会了agent的核心原理！'写到 result.txt，然后再读出来告诉我内容")
