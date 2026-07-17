'''
题目：求s=a+aa+aaa+aaaa+aa...a的值，其中a是一个数字。例如2+22+222+2222+22222(此时共有5个数相加)，几个数相加有键盘控制。  
1.程序分析：关键是计算出每一项的值
'''

def calculate(a, n):
    _sum = 0
    for i in range(n):
        _sum += a * (10 ** i) * (n - i)
    print(f"result : {_sum}")


