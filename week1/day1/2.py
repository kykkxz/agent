cache = {(5, 2): 25}
def cache_func(func):
    def wrapper(*args):
        try:
            if args in cache:
                print("命中缓存,直接读取")
                return cache[args]
            res = func(*args)
            cache[args] = res
            return res
        except Exception as e:
            print(f"函数{func.__name__}发生异常:{e}")
            raise
    return wrapper

@cache_func
def big_calc(a,b):
    print("复杂计算中...")
    return a**b

big_calc(5,2)
big_calc("撒大大", "撒大大撒")
print(cache)
