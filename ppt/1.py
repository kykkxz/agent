from openai import OpenAI

client = OpenAI(api_key="sk-2e52676748864aa8a2fbf319aca591bd", base_url="https://api.deepseek.com")

response = client.responses.create(
    model="deepseek-v4-flash",
    instructions="You are a helpful assistant.",
    input="Hi, how are you?",
)

print(response.output_text)