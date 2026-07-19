# 1. Python的装饰器是什么。
    在不改变原函数代码、也不改变原函数调用方式的前提下，给函数增加新功能.
    核心应用场景
    日志记录： 在函数执行前后自动打印日志，记录谁在什么时候调用了该函数。

    性能测试： 统计函数执行了多长时间。

    权限校验： 检查当前用户有没有登录。如果没登录，直接拦截，不执行后面的业务函数。

    缓存机制： 如果函数用相同的参数调用过，直接从内存拿结果，不用重新计算.

# 2. Python中常见的库有哪些
    os， sys， datetime， random， math， threading， json

# 3. Python 中类属性和实例属性有什么区别？如果多个对象同时修改类属性，会产生什么影响？
    区别：
    类属性： 属于类本身，所有实例共享同一份数据。它在内存中只有一份（比如定义在类内部、方法外部的变量）。
    实例属性： 属于具体的某个对象（实例），每个对象独享自己的数据（通常在 __init__ 中用 self.name = ... 定义）。
    修改类属性的影响：
    如果直接通过类名修改（如 Drink.price = 15），所有实例看到的属性都会同步改变。
    如果通过实例去修改（如 apple_drink.price = 15），Python 并不会修改类属性，而是会在这个特定实例上偷偷创建一个同名的实例属性，从而把类属性“遮蔽”掉。其他实例不受影响。
# 4. __init__ 方法的作用是什么？子类重写 __init__ 时为什么通常要调用 super().__init__()？
    __init__ 的作用： 它是初始化构造器。当对象创建好后，__init__ 负责给这个新对象初始化。

    为什么要调用 super().__init__()：
    如果子类重写了 __init__，父类的初始化代码默认就会被完全覆盖。这意味着父类里定义的属性（比如一些基础配置、公用变量）在子类中根本不会被创建。调用 super().__init__() 就是为了执行父类的初始化逻辑，避免代码重复。

# 5. 什么是继承和方法重写？请结合“饮品类”或“考试类”举例说明。
    继承： 子类自动获得父类的属性和方法，避免重复造轮子。

    方法重写： 子类觉得父类的方法不够个性化，自己重新写一个同名方法来覆盖父类的行为。
```python
    class BaseExam(ABC):
    passing_rate: float = 0.6

    def __init__(self, subject_name: str, max_score, student_name) -> None:
        if not self.check_student_name(student_name):
            raise ValueError("学生姓名不能为空")
        if max_score <= 0:
            raise ValueError("满分必须大于 0")

        self.subject_name: str = subject_name
        self.max_score: float = float(max_score)
        self.student_name: str = student_name
        self.__score = 0.0

    def get_score(self):
        return self.__score

    class ChineseExam(BaseExam):
    def __init__(self, student_name: str, essay_score : float) :
        super().__init__("语文", 150, student_name)

        if not 0 <= essay_score <= 60:
            raise ValueError("作文分必须在 0 到 60 之间")
        self.essay_score: float = float(essay_score)

    def get_grade(self, score: float):
        if score >= 135:
            return "优秀"
        if score >= 120:
            return "良好"
        if score >= 90:
            return "及格"
        return "不及格"
```

# 6 . 抽象类和抽象方法有什么作用？为什么 BaseExam / BaseDrink 这类基类适合设计成抽象类？
    抽象类就像是一个法律合同或设计蓝图。它只规定“有什么功能”，而不实现具体细节。

    为什么适合做基类：
    像 BaseDrink或 BaseExam这种概念太抽象了。在现实中，你无法做出一个“纯粹的、没有种类的饮品”。直接实例化它们没有意义。把它们设计成抽象类，可以强制要求所有子类必须实现指定的抽象方法。如果不实现，Python 报错不让运行，从而保证了代码的规范性。
# 7. 什么是多态？为什么主程序可以把 ChineseExam、MathExam、EnglishExam 放在同一个列表里统一调用方法？
    "多态"是指同一操作作用于不同的对象，可以有不同的解释，产生不同的执行结果。

    为什么能放在同一个列表里：
    因为 ChineseExam、MathExam、EnglishExam 都继承自 BaseExam，并且都重写了相同名字的方法。只要这些对象有相同的方法，主程序就不需要关心它们具体是什么科目。

# 8. 多线程中为什么会出现数据竞争？在成绩录入或库存扣减场景中，为什么需要 threading.Lock()？
    在多线程中，所有线程共享进程的内存。像 count += 1 这样看似只有一行的 Python 代码，在底层其实分为三步：读取旧值 -> 加上 1 -> 写入新值。如果线程 A 刚读了旧值，还没来得及写回去，操作系统就把 CPU 切换给了线程 B，线程 B 也去读了旧值，就会导致两个线程的数据互相覆盖，结果出错。

    在成绩录入或库存扣减时，数据准确性是第一位的。Lock（线程锁）就像是洗手间的门锁。一个线程进入修改数据的“核心区域”前，先调用 lock.acquire() 把门锁上，其他线程只能在外面排队等着；等这个线程修改完毕，调用 lock.release() 开锁，下一个线程才能进去。这样就保证了同一时刻只有一个线程能操作该数据，防止数据被“改脏”。
# 9.  串行执行和多线程并发执行有什么区别？什么类型的任务更适合用多线程优化？
    串行执行： 像排队办事，一件事情做完了，才能做下一件。
    并发执行： 多个任务交替执行，或者多核同时执行，看起来像是在“同时进行”。

    I/O 密集型任务（极度适合）： 比如网络爬虫、文件读写、数据库查询。这类任务大量时间都在“等”（等网络响应、等硬盘读写），多线程可以在一个线程等待时，让另一个线程去干活，极大提升效率。

# 10.  with open(...) 相比手动 open() / close() 有什么好处？在文件读写中它能避免哪些问题？
    with 语句使用了 Python 的上下文管理器协议。它最大的好处就是：无论发生什么，它都会自动帮你关闭文件。
    能避免哪些问题：
    忘记关闭文件： 导致内存泄露，文件被长期占用。
    程序崩溃导致无法关闭： 如果你手动写 f.close()，但在 close() 之前程序抛出了异常崩溃了，文件就永远不会被正常关闭。而 with 块即使内部代码报错崩溃，在退出时也会雷打不动地执行关闭操作，极其安全。