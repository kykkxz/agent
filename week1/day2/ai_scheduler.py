'''
Python 综合作业：AI 推理任务指挥官

一、基础信息

分值：30 分 | 完成时长：90 分钟提交：`ai_scheduler.py`源码 + 运行截图 + 思考题答案二、考察知识点

类与继承、抽象接口、多线程、线程锁、datetime 耗时统计、分层编程三、功能要求

### 1. 模型层

1. 父类`AIModel`：含 name、model_type；`predict`抛出`NotImplementedError`
2. `TextModel`子类：推理休眠 1s，返回推理结果与耗时
3. `ImageModel`子类：推理休眠 2s，返回识别结果与耗时

### 2. 调度器 Scheduler

* 属性：任务记录表`records`、线程锁`lock`
* `_run_one`：执行单任务，加锁写入记录
* `run_serial`：串行依次执行所有任务
* `run_concurrent`：多线程并发执行，start+join 等待全部结束
* `report`：格式化打印每条任务详情

### 3. 主程序 main

1. 创建文本、图像模型，构造≥6 条混合用户任务
2. 分别运行串行、并发，用 datetime 统计全局总耗时
3. 输出对比报表：串行总耗时、并发总耗时、节省时长、加速比、当前系统时间

四、代码规范（5 分）

1. 所有类、方法添加文档注释
2. 分层清晰、命名规范、无报错无冗余代码

五、加分拓展（+5 分，选做）

1. 新增语音模型 AudioModel，扩充任务列表
2. 将性能报表写入 report.txt
3. 用 ThreadPoolExecutor 实现线程池版本

六、思考题（5 分，必写）

1. 多线程写入 records 为什么要加 Lock？不加锁会出现什么问题？
2. 本案例多线程能提速，纯 CPU 计算场景还能加速吗？为什么？
3. 父类抛出 NotImplementedError 是什么设计思想，作用是什么？

七、扣分标准

1. 无继承抽象结构 -8 分
2. 并发未加锁 -6 分
3. 缺失串行 / 并发任一模式 -7 分
4. 性能报表信息不全 -4 分
5. 无注释、格式混乱 2~5 分
6. 代码报错、日志缺失每项 -3 分
7. 不交思考题 -5 分

交付文件

1. ai_scheduler.py
2. 完整运行截图
3. 思考题文字解答
4. 以上放在github个人项目地址
'''

import time
from datetime import datetime
import threading

# AI模型基类
class AIModel:
    def __init__(self, name : str, model_type : str):
        self.name = name
        self.model_type = model_type
# 虚函数接口
    def predict(self, input_data : str):
        raise NotImplementedError("子类必须实现 predict() 方法以进行具体的推理逻辑。")

# 文本模型
class TextModel(AIModel):
    def __init__(self, name : str, model_type : str = "文本模型"):
        super().__init__(name, model_type)

    def predict(self, input_data : str):
        start = datetime.now()
        print(f"文本模型{self.name}正在生成文本...")
        time.sleep(1)

        end = datetime.now()

        cost = (end - start).total_seconds()
        return {
            "model_name": self.name,
            "model_type": self.model_type,
            "input": input_data,
            "result": f"【文本生成完毕】已回复: {input_data}...",
            "cost": cost
        }

# 图像模型
class ImageModel(AIModel):
    def __init__(self, name : str, model_type : str = "图像模型"):
        super().__init__(name, model_type)

    def predict(self, input_data : str):
        start = datetime.now()
        print(f"图像模型{self.name}正在识别图像...")
        time.sleep(2)

        end = datetime.now()
        cost = (end - start).total_seconds()
        
        return{
            "model_name": self.name,
            "model_type": self.model_type,
            "input": input_data,
            "result": f"【图像识别成功】检测到物体: {input_data}",
            "cost": cost
        }

# 语音模型
class AudioModel(AIModel):
    def __init__(self, name, model_type = "语音模型"):
        super().__init__(name, model_type)

    def predict(self, input_data : str):
        start = datetime.now()
        print(f"语音模型{self.name}正在理解语音...")
        time.sleep(2)

        end = datetime.now()
        cost = (end - start).total_seconds()
        
        return{
            "model_name": self.name,
            "model_type": self.model_type,
            "input": input_data,
            "result": f"语音转录文本: {input_data}",
            "cost": cost
        }

# 调度器类
class Scheduler:
    def __init__(self):
        self.records = []
        self.lock = threading.Lock()

    def clear_records(self):
        self.records = []
    # 单次执行
    def _run_one(self, model : AIModel, input_data : str):
        result = model.predict(input_data)

        with self.lock:
            self.records.append(result)
    # 串行执行一系列任务
    def run_serial(self, tasks : list):
        print("-----------串行执行任务-------------")
        self.clear_records()
        for model, input_data in tasks:
            self._run_one(model, input_data)

    # 并行执行一系列任务
    def run_concurrent(self, tasks : list):
        print("-----------并行执行任务-------------")
        self.clear_records()
        threads = []

        for model, input_data in tasks:
            t = threading.Thread(target=self._run_one, args=(model, input_data))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    # 生成报表
    def report(self):
        report_lines = []
        header = f"{'模型名称'} | {'模型类型'} | {'输入数据'} | {'耗时 (秒)'} | {'推理结果'}"
        report_lines.append(header)
        report_lines.append("-" * 80)
        
        for r in self.records:
            line = f"{r['model_name']} | {r['model_type']} | {r['input']} | {r['cost']} | {r['result']}"
            report_lines.append(line)
            
        report_content = "\n".join(report_lines)
        print(report_content)
        return report_content


def main():
    """主逻辑：初始化任务，运行并对比性能，生成最终报告。"""
    # 1. 初始化各类模型
    gpt = TextModel("GPT")
    deepseek = TextModel("DeepSeek")
    yolo = ImageModel("YOLO")
    resnet = ImageModel("Image2")
    whisper = AudioModel("Whisper")
    sensevoice = AudioModel("QWEN-TTS-FLASH")

    # 2. 构造 6 条混合用户任务 (Text * 2, Image * 2, Audio * 2)
    tasks = [
        (gpt, "写一首关于写代码的诗"),
        (yolo, "camera_entry_flow.jpg"),
        (whisper, "meeting_record_01.wav"),
        (deepseek, "解释什么是量子纠缠"),
        (resnet, "medical_scan_lung.png"),
        (sensevoice, "customer_voice_call.mp3")
    ]

    scheduler = Scheduler()

    # 3. 串行运行测试
    serial_start = datetime.now()
    scheduler.run_serial(tasks)
    serial_end = datetime.now()
    serial_total_cost = (serial_end - serial_start).total_seconds()
    print("\n--- 串行执行结果明细 ---")
    serial_details = scheduler.report()

    # 4. 并发运行测试
    concurrent_start = datetime.now()
    scheduler.run_concurrent(tasks)
    concurrent_end = datetime.now()
    concurrent_total_cost = (concurrent_end - concurrent_start).total_seconds()
    print("\n--- 并发执行结果明细 ---")
    concurrent_details = scheduler.report()

    # 5. 性能数据分析计算
    time_saved = serial_total_cost - concurrent_total_cost
    speedup_ratio = serial_total_cost / concurrent_total_cost if concurrent_total_cost > 0 else 0
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 6. 构建汇总对比报表
    summary_report = f"""
【基本信息】
当前系统时间: {current_time_str}
任务总数量: {len(tasks)} 个

【耗时数据】
串行总耗时: {serial_total_cost:.4f} 秒
并发总耗时: {concurrent_total_cost:.4f} 秒

【性能表现】
节省时长: {time_saved:.4f} 秒
系统加速比: {speedup_ratio:.2f} 倍

【设计验证】
由于多线程并发，并发总耗时应逼近“耗时最长的主单任务耗时”。
验证结果: 并发耗时约 {concurrent_total_cost:.2f}s
"""
    # 打印系统汇总报告
    print(summary_report)

    # 7. 写入 report.txt (加分项)
    try:
        with open("report.txt", "w", encoding="utf-8") as f:
            f.write(summary_report)
            f.write("\n\n--- 附录1：串行运行单项明细 ---\n")
            f.write(serial_details)
            f.write("\n\n--- 附录2：并发运行单项明细 ---\n")
            f.write(concurrent_details)
        print("性能报表已写入\n")
    except IOError as e:
        print(f"写入文件失败: {e}")


if __name__ == "__main__":
    main()
