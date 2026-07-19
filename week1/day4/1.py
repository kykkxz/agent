'''
🎯 任务一（基础关，约 15 分钟）：异步打招呼

要求：

1. 写 `async def greet(name, delay)`：`await asyncio.sleep(delay)` 后，打印 `f"Hello, {name}!"` 并返回 `name`。
2. 用 `asyncio.gather` 同时跑 3 个：`("Alice", 1)`、`("Bob", 2)`、`("Carol", 3)`。
3. 打印返回的结果列表，打印总耗时（应该约 3 秒）。
'''
from datetime import datetime
import asyncio
async def greet(name, delay):
    await asyncio.sleep(delay)
    
    print(f"Hello, {name}!")
    return name

async def main():
    start = datetime.now()
    await asyncio.gather(greet("Alice" , 1), greet("Bob", 2), greet("Carol", 3))
    end = datetime.now()
    cost = (end - start).total_seconds()
    print(f"总耗时:{cost}")

if __name__ == "__main__":
    asyncio.run(main())
