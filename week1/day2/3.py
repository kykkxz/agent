'''
1. 写一个函数 `simulate_inference(model_name, seconds)`，里面 `print` 开始信息，`time.sleep(seconds)` 模拟推理，再 `print` 结束信息。
2. 用 `datetime.now()` 记录开始和结束时间，算出总耗时。
3. 先**串行**调用 4 次（每次 1 秒），打印串行总耗时。
4. 再用**多线程**同时调用 4 次（每次 1 秒），打印多线程总耗时。
5. 对比两个耗时，体会并发加速效果。

'''
import time
from datetime import datetime
import threading

records = []
records_lock = threading.Lock()

def simulate_inference(model_name, seconds):
    print("开始")
    start = datetime.now()
    start_str = start.strftime("%H:%M:%S.%f")[:-3]

    time.sleep(seconds)

    end = datetime.now()
    end_str = end.strftime("%H:%M:%S.%f")[:-3]
    print("结束")

    cost = (end - start).total_seconds()
    
    with records_lock:
        records.append({
            "model": model_name,
            "start": start_str,
            "end": end_str,
            "cost": round(cost, 3)
        })

print("---------串行测试----------")
start = datetime.now()

simulate_inference("a", 1)
simulate_inference("a", 1)
simulate_inference("a", 1)

end = datetime.now()

duration = (end - start).total_seconds()
print("---------串行测试----------")

print(f"串行花费:{duration}")

print("---------并行测试----------")
start_paraller = datetime.now()
threads = []

for i in range(4):
    t = threading.Thread(target=simulate_inference, args=(f"{i+1}", 1))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("---------并行测试----------")

end_paraller = datetime.now()

duration_paraller = (end_paraller - start_paraller).total_seconds()
print(f"并行花费:{duration_paraller}")

print("并行任务明细")

for rec in records:
    print(f"模型: {rec['model']} | 开始: {rec['start']} | 结束: {rec['end']} | 耗时: {rec['cost']} 秒")
