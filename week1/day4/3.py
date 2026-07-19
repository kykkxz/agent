'''
要求（复用第三天的 AI 模型骨架，改成异步）：

1. 定义 `AIModel` 基类，`async def predict(self, input_data)` 抛 `NotImplementedError`。
2. 子类 `TextModel`：`predict` 里 `await asyncio.sleep(1)`，返回 `f"文本结果:{input_data}"`。
3. 子类 `ImageModel`：`predict` 里 `await asyncio.sleep(2)`，返回 `f"图像结果:{input_data}"`。
4. 写 `async def user_request(user, model, input_data)`：记录开始/结束时间，`await model.predict(...)`，返回 `{user, model, cost, result}`。
5. 用 `gather` 同时跑 4 个用户请求（2 个文本、2 个图像），打印每个用户耗时和总耗时。
'''
from datetime import datetime
import asyncio

class AIModel:
    def __init__(self, name : str, model_type : str):
        self.name = name
        self.model_type = model_type

    async def predict(self, input_data : str) -> str:
        raise NotImplemented("子类必须实现此方法")


class TextModel(AIModel):
    def __init__(self, name, model_type = "文本模型"):
        super().__init__(name, model_type)

    async def predict(self, input_data : str):
        print(f"文本模型{self.name}正在生成文本...")
        await asyncio.sleep(1)
        return f"生成的文本结果: {input_data}"

class ImageModel(AIModel):
    def __init__(self, name, model_type = "图像模型"):
        super().__init__(name, model_type)

    async def predict(self, input_data : str):
        print(f"图像模型{self.name}正在识别图像...")
        await asyncio.sleep(2)
        return f"识别结果: {input_data}"

async def user_request(user, model, input_data):
    start = datetime.now()

    result = await model.predict(input_data)
    
    end = datetime.now()
    cost = (end - start).total_seconds()
    return {
        "user": user, 
        "model_name": model.name, 
        "cost": cost, 
        "result": result
    }


async def main():
    # 初始化模型
    gpt = TextModel("ChatGPT-5")
    mj = ImageModel("Image2")
    
    print("=== 开始并发处理用户请求 ===")
    
    # 使用 gather 同时跑 4 个请求（2个文本，2个图像）
    results = await asyncio.gather(
        user_request("小明", gpt, "写一首关于Python的诗"),
        user_request("小红", gpt, "请假条怎么写？"),
        user_request("大壮", mj, "生成一只赛博朋克猫咪"),
        user_request("翠花", mj, "生成美丽的富士山风景")
    )
    
    
    print("\n=== 各用户请求处理结果 ===")
    for res in results:
        print(f"用户: {res['user']} | 使用模型: {res['model_name']} | 耗时: {res['cost']:.2f}秒 | 结果: {res['result']}")
        

if __name__ == "__main__":
    asyncio.run(main())
