'''
1. 定义 `AIModel` 类，属性：`name`（模型名）、`model_type`（模型类型）。
2. 有方法 `predict(self, input_data)`：父类里只打印"XX模型收到输入：XX，但具体推理逻辑由子类实现"，并 `return "父类默认结果"`。
3. 定义子类 `TextModel`（文本模型），重写 `predict`：用 `time.sleep(1)` 模拟推理耗时 1 秒，打印"文本模型XX正在生成文本..."，返回 `f"生成的文本结果: {input_data}"`。
4. 定义子类 `ImageModel`（图像模型），重写 `predict`：用 `time.sleep(2)` 模拟推理耗时 2 秒，打印"图像模型XX正在识别图像..."，返回 `f"识别结果: {input_data}"`。
5. 分别创建一个文本模型和一个图像模型，调用 `predict`，打印返回结果。
6. 复用上午任务三写的 `AIModel`、`TextModel`、`ImageModel` 类。
7. 写一个函数 `user_request(user_name, model, input_data)`：
  * 记录开始时间
  * 调用 `model.predict(input_data)` 拿到结果
  * 记录结束时间，算耗时
  * 用锁把 `{user, model名, cost, result}` 存进全局列表
8. 创建 1 个 TextModel、1 个 ImageModel。
9. 起 4 个线程模拟 4 个用户同时请求（两个用户请求文本模型，两个请求图像模型）。
10. 跑完打印每个用户的请求耗时和结果，再打印总耗时。
'''
import time
from datetime import datetime
import threading
class AIModel:
    def __init__(self, name : str, model_type : str):
        self.name = name
        self.model_type = model_type

    def predict(self, input_data : str) -> str:
        print(f"{self.name}模型收到输入：{input_data}，但具体推理逻辑由子类实现")
        return f"父类默认结果"

class TextModel(AIModel):
    def __init__(self, name, model_type = "文本模型"):
        super().__init__(name, model_type)

    def predict(self, input_data : str) -> str:
        print(f"文本模型{self.name}正在生成文本...")
        time.sleep(1)
        return f"生成的文本结果: {input_data}"

class ImageModel(AIModel):
    def __init__(self, name, model_type = "图像模型"):
        super().__init__(name, model_type)

    def predict(self, input_data : str) -> str:
        print(f"图像模型{self.name}正在识别图像...")
        time.sleep(2)
        return f"识别结果: {input_data}"
text = TextModel("1")
print(text.predict("21312"))

image = ImageModel("2")
print(image.predict("213124124"))


print("----------------多线程测试-----------------")
records = []
records_lock = threading.Lock()
threads = []
def user_request(user_name, model, input_data):
    start = datetime.now()

    result = model.predict(input_data)

    end = datetime.now()

    cost = (end - start).total_seconds()
    with records_lock:
        records.append({
            "user" : user_name,
            "model" : model.name,
            "cost" : cost,
            "result" : result
        })

for i in range(4):
    if i < 2:
        model = text
    else:
        model = image
    t = threading.Thread(target=user_request, args=(f"{i+1}", model, f"12313"))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

for rec in records:
    print(f"用户: {rec['user']} | 模型: {rec['model']} | 耗时: {rec['cost']} | 结果: {rec['result']} 秒")
    
