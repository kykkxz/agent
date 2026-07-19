'''
🎯 任务二（进阶关，约 15 分钟）：三种方式大对比

要求：

1. 写一个"模拟推理"的活：等 1 秒，返回结果。
2. 分别用**串行**（一个一个来）、**多线程**、**异步**三种方式跑 5 个活。
3. 用 `datetime` 记录每种方式的总耗时，打印出来对比。
'''
import time
from datetime import datetime
import asyncio
import threading

def simulate():
    print("正在推理")
    time.sleep(1)

async def assimulate():
    print("正在异步推理")
    await asyncio.sleep(1)

def liner():
    start = datetime.now()
    for i in range(5):
        simulate()
    end = datetime.now()
    cost = (end - start).total_seconds()

    print(f"串行耗时{cost}秒")

def thread():
    _ = []
    start = datetime.now()
    for i in range(5):
        t = threading.Thread(target = simulate)
        t.start()
        _.append(t)
    for i in _:
        i.join()
    end = datetime.now()
    cost = (end - start).total_seconds()

    print(f"并行耗时{cost}秒")

async def asio():
    start = datetime.now()
    
    await asyncio.gather(assimulate(), assimulate(), assimulate(), assimulate(), assimulate())
    

    end = datetime.now()
    cost = (end - start).total_seconds()

    print(f"异步耗时{cost}秒")

if __name__ == "__main__":
    liner()
    thread()
    asyncio.run(asio())
