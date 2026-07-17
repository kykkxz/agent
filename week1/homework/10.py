'''
题目：一球从100米高度自由落下，每次落地后反跳回原高度的一半；再落下，求它在   第10次落地时，共经过多少米？第10次反弹多高？
'''
def calculate(n):
    _sum = 0
    start = 100
    back = start / (2**n)
    _sum = 100 + 2 * 100 * (1 - 0.5 ** (n - 1))
    print(f"经过{n}次后\n进过{_sum}米")
    print(f"反弹{back}米")

calculate(10)
