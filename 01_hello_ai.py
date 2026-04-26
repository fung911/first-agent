import anthropic
from config import API_KEY, BASE_URL, MODEL

# 创建客户端，指向 DeepSeek 的 Anthropic 兼容接口
client = anthropic.Anthropic(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# 发送一条消息，等待回复
response = client.messages.create(
    model=MODEL,
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "你好，用一句话介绍你自己"}
    ]
)

# DeepSeek 返回多个 block：ThinkingBlock（思考过程）+ TextBlock（真正回复）
# 找到 TextBlock 才是我们要的内容
for block in response.content:
    if block.type == "text":
        print(block.text)
