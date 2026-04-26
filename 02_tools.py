import anthropic
from config import API_KEY, BASE_URL, MODEL

client = anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)

# ── 第一部分：定义工具"说明书" ──────────────────────────────────────────
# 这里只是告诉 AI "你有这些工具，它们能做什么"
# AI 自己决定什么时候调用，不需要你告诉它
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

# ── 第二部分：真正执行工具的函数 ─────────────────────────────────────────
# AI 说"我要调用 write_file"，但真正写文件的是这里的普通 Python 代码
def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"已成功写入 {path}"

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def execute_tool(name, inputs):
    print(f"  [工具执行] {name}({inputs})")
    if name == "write_file":
        return write_file(inputs["path"], inputs["content"])
    if name == "read_file":
        return read_file(inputs["path"])
    return "未知工具"

# ── 第三部分：发送请求，看 AI 怎么决定用工具 ─────────────────────────────
response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "帮我把'我觉得好棒啊，我搞清楚了agent的基本原理'写到 hello.txt 文件里"}
    ]
)

print(f"stop_reason: {response.stop_reason}")
print(f"content blocks: {[b.type for b in response.content]}")
print()

# ── 第四部分：处理 AI 的响应 ──────────────────────────────────────────────
for block in response.content:
    if block.type == "text":
        print(f"AI 说: {block.text}")

    if block.type == "tool_use":
        # AI 决定要调用工具了，block 里有工具名和参数
        print(f"AI 想调用工具: {block.name}")
        print(f"AI 传的参数: {block.input}")

        # 我们去真正执行它
        result = execute_tool(block.name, block.input)
        print(f"工具返回: {result}")
