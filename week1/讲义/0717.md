# # 0717工作目标

1. 奶茶管理系统项目回顾

2. 知识点回顾：
   1）项目框架
   2）with
   3 ) python运行环境的知识

3. 类装饰器

4. 异步，异步vs多线程的区别

5. 学生成绩管理系统 ，prd和技术文档，venv /requirements.txt/readme.py （1-2小时）
   
   

## 一、类装饰器

1. 基本概念：自定义的一个类当做装饰(@类名)去修饰普通函数
   前提条件：类必须定义2个魔法方法
   
   ```
   __init__(self, func):装饰初始化，接收被装饰的函数，仅执行一次
   __call___(self, *args, **kwargs):让类的实例编程一个可调用对用，每次调用原函数都会执行
   ```

2. 核心作用
   1）新增一些前后逻辑（日志，校验，缓存），和普通函数装饰器是一样
   2）持久保存数据状态（缓存内容，计数，时间记录），靠self.xxx实例属性存储
   3）兼具类的作用，类中的方法可以操作类的属性
   4）带参数的装饰器，分层条理清洗，不用多层嵌套
   5 ）支持资源声明周期管理（链接，需要销毁）

3. vs普通函数装饰器的区别
   普通装饰器：无状态存储需求，简单逻辑
   类装饰器：带持久状态，需要与外部进行交互，相对复杂的场景
   
   ### 2.基础标准示例（无参类装饰器
   
      
   
   ```python
   # 打印函数执行前后日志
   
   class LogDecorator:
       def __init__(self, func):
           self.func = func
       def __call__(self, *args, **kwargs):
           print(f"=====开始执行函数{self.func.__name__}===========")
           result = self.func(*args, **kwargs)
           print(f"=====函数执行结果：result===========")
           return result
   
   #使用类作为装饰器
   
   @LogDecorator
   def add(a, b):
       return a + b
   
   
   ```

```

```

```

```

@LogDecorator
def mul(a, b):
    return a - b

add(2,3)
add(5,2)

```

```python
def log_record(func):
 def wrapper(*args,**kwargs):
     import time
     start = time.time()
     res = func(*args,**kwargs)
     cost = time.time()-start
     print(f"调用{func.__name__}，耗时{cost:.2f}s")
     return res
 return wrapper

@log_record
def calc_damage(base):
 return base * 1.5
```

示例2：带参数的类装饰器

如果装饰器是需要传入自定义的阐述，__init__接收配置，__call__接收函数

```python
class Logger:
    def __init__(self, level="INFO"):
        self.level = level

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            print(f"[{self.level}]调用函数：{func.__name__}")
            return func(*args, **kwargs)
        return wrapper

# 给装饰器传参
@Logger("DEBUG")
def login(name):
    print(f"登录用户：{name}")

login("张三")
```

3.常见的应用场景：

场景1. 缓存

```python
# 全局缓存字典（所有被装饰函数共用同一个cache）
cache = {}

def cache_func(func):
    def wrapper(*args):
        # 判断参数元组是否存在缓存
        if args in cache:
            return cache[args]
        # 不存在则执行原函数
        res = func(*args)
        # 存入缓存
        cache[args] = res
        return res
    return wrapper

# 装饰等价于 big_calc = cache_func(big_calc)
@cache_func
def big_calc(a,b):
    print("复杂计算中...")
    return a**b
```

核心缺陷：

1.全局共享缓存，多个函数会污染缓存

2.无法手动清空缓存

```python
@cache_func
def add(x,y):
    return x+y

add(2,3)
```

```python
# 类装饰器实现缓存管理
class CacheDecorator:
    def __init__(self, func):
        self.func = func
        self._cache = {}

    def __call__(self, *args):
        if args in self._cache:
            return self._cache[args]
        res = self.func(*args)
        self._cache[args] = res 
        return res

    def clear(self):
        self._cache.clear()
        print("缓存已清空")

    #新增获取缓存的方法
    def get_cache(self):
        return self._cache

@CacheDecorator
def big_calc(a,b):
    print("复杂计算中...")
    return a**b

@CacheDecorator
def add(a,b):
    return a + b

# 函数也是一个对象
print(big_calc(3,2))

print(big_calc.get_cache())
print(add(3,2))
print(add.get_cache())
big_calc.clear()
print(big_calc.get_cache())
print(add.get_cache())


##
复杂计算中...
9
{(3, 2): 9}
5
{(3, 2): 5}
缓存已清空
{}
{(3, 2): 5}
```

场景2：统计函数调用次数

```python
class CallCounter:
    def __init__(self, func):
        self.func = func
        self.count = 0  # 实例属性永久保存计数

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"函数 {self.func.__name__} 已调用 {self.count} 次")
        return self.func(*args, **kwargs)

    # 拓展自定义方法：外部可主动查看次数
    def get_count(self):
        return self.count

@CallCounter
def hello():
    print("Hello World")

hello()
hello()
hello()
# 外部调用装饰器实例的方法
print("总调用次数：", hello.get_count())
```

场景3：接口限流（记录时间窗口内调用记录

需求

限制函数10秒内最多调用3次，存储每次调用的时间戳做判断。

```python
import time

class RateLimit:
    # 装饰器传参：最大次数、时间窗口
    def __init__(self, max_times=3, window=10):
        self.max_times = max_times
        self.window = window
        self.record = []  # 保存每次调用的时间戳

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()
            # 清理超时的记录
            self.record = [t for t in self.record if now - t < self.window]
            if len(self.record) >= self.max_times:
                raise Exception("请求过于频繁，请稍后再试")
            self.record.append(now)
            return func(*args, **kwargs)
        return wrapper

# 10秒最多调用2次
@RateLimit(max_times=2, window=10)
def send_msg(phone):
    print(f"向 {phone} 发送短信")

send_msg("13800000000")
send_msg("13800000000")
send_msg("13800000000")  # 抛出限流异常
```

优先使用类装饰器：需要保存状态，外部需要操作内部数据，资源管理

优先是使用普通函数装饰器：简单无状态逻辑（打印、计时、参数打印），追求极简代码。

## 二、异步

1.异步：一个工人，特别会统筹，等着干一件事的时候，就赶紧去干另一件事

AI：agent-->调用，cpu去服务于别的用户。

模拟"多个用户请求AI模型"

2.同步vs异步

sync同步： time.sleep(2)

async异步：await asyncio.sleep(2)

3.关键词

async def ：定义一个特殊函数，协程函数，注意：调用时并不会立马执行，只是获得一个任务单

await：等一下

asyncio.run(...)：总开关，启动整个一步系统，程序入口

4.示例对比

```python
# # 同步版
# import time

# def task(name):
#     print(f"{name} 开始")
#     time.sleep(2)        # 同步等待：真的卡住2秒
#     print(f"{name} 结束")

# task("A")
# task("B")
# task("C")
# # 总共要 6 秒（3个 × 2秒，一个一个来）


#异步版
import asyncio
import time

async def task(name):              # ← 注意多了 async
    print(f"{name} 开始")
    await asyncio.sleep(2)         # ← 注意用 await 和 asyncio.sleep
    print(f"{name} 结束")

async def main():
    start = time.time()
    # gather 并发执行多个任务
    await asyncio.gather(task("A"), task("B"), task("C"))
    end = time.time()
    print(f"异步版耗时：{end - start} 秒")  # ← 注意用 end - start

# async def main():
#     start = time.time()
#     # gather 并发执行多个任务
#     await task("A")
#     await task("B")
#     await task("C")
#     end = time.time()
#     print(f"耗时：{end - start} 秒")  # ← 注意用 end - start

asyncio.run(main())  # ← 总开关，启动

```

```python
import asyncio
import time

async def compute(name, x):              # ← 注意多了 async
    await asyncio.sleep(1)         # ← 注意用 await 和 asyncio.sleep
    print(f"{name} 的结果是 {x*2}")

async def main():
    start = time.time()
    # gather 并发执行多个任务
    result = await asyncio.gather(
        compute("A", 5),
        compute("B", 10),
        compute("C", 15),
    )
    end = time.time()
    print(f"耗时：{end - start} 秒")  # ← 注意用 end - start
    print(result)

asyncio.run(main())  # ← 总开关，启动
```



**随堂任务**：

写一个异步函数 `fetch(name, delay)`：等 `delay` 秒后，返回 `f"{name}完成"`。用 `gather` 同时跑 3 个（分别等 1、2、3 秒），打印结果列表和总耗时。



## 三、多线程vs异步

|             | 多线程      | 异步              |
| ----------- | -------- | --------------- |
| 谁来干活        | 多个线程     | 一个线程里的多个协程      |
| 切换成本        | 高（操作系统）  | 低（自己切换）         |
| 占内存         | 每个线程MB   | 每个写成几个kb        |
| 适合干啥        | 等待型+少量计算 | 大量等待（网络请求、模型推理） |
| 写代码         | 普通函数     | async、await，调用链 |
| 多个任务去改同一个数据 | 加锁       | 单线程，按顺序，不需要加锁   |

```python
#多线程
import threading
import time

def task(name):
    print(f"{name} 开始")
    time.sleep(2)
    print(f"{name} 结束")

threads = [threading.Thread(target=task, args=(f"T{i}",)) for i in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
# 约 2 秒
```

```python
#异步版

import asynico

async def task(name):
    print(f"{name} 开始")
    await asyncio.sleep(2)
    print(f"{name} 结束")


async def main():
    await asyncio.gather(*[task(f"T{i}]") for i in range(3)]


asynico.run(main())
```

```python

async def task():           # 这个是异步
    ...

async def main():           # 调它的也得是异步
    await task()            # 必须用 await

asyncio.run(main())         # 最外面得用 asyncio.run 启动
```

![ebbbe868-61c4-4207-9bd3-ca1f89479651](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/ebbbe868-61c4-4207-9bd3-ca1f89479651.png)

## 四、任务

🎯 任务一（基础关，约 15 分钟）：异步打招呼

要求：

1. 写 `async def greet(name, delay)`：`await asyncio.sleep(delay)` 后，打印 `f"Hello, {name}!"` 并返回 `name`。
2. 用 `asyncio.gather` 同时跑 3 个：`("Alice", 1)`、`("Bob", 2)`、`("Carol", 3)`。
3. 打印返回的结果列表，打印总耗时（应该约 3 秒）。
   
   

🎯 任务二（进阶关，约 15 分钟）：三种方式大对比

要求：

1. 写一个"模拟推理"的活：等 1 秒，返回结果。
2. 分别用**串行**（一个一个来）、**多线程**、**异步**三种方式跑 5 个活。
3. 用 `datetime` 记录每种方式的总耗时，打印出来对比。
   
   

🎯 任务三（挑战关，约 20 分钟）：异步模拟多用户请求

要求（复用第三天的 AI 模型骨架，改成异步）：

1. 定义 `AIModel` 基类，`async def predict(self, input_data)` 抛 `NotImplementedError`。
2. 子类 `TextModel`：`predict` 里 `await asyncio.sleep(1)`，返回 `f"文本结果:{input_data}"`。
3. 子类 `ImageModel`：`predict` 里 `await asyncio.sleep(2)`，返回 `f"图像结果:{input_data}"`。
4. 写 `async def user_request(user, model, input_data)`：记录开始/结束时间，`await model.predict(...)`，返回 `{user, model, cost, result}`。
5. 用 `gather` 同时跑 4 个用户请求（2 个文本、2 个图像），打印每个用户耗时和总耗时。


