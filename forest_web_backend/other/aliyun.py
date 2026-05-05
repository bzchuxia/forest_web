import dashscope
dashscope.api_key = "sk-709522d3f0f94b57852aefe1e9519419"
response = dashscope.Generation.call(
    model="qwen-turbo",
    prompt="你好，请说一句话"
)
print(response)