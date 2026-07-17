'''
题目：给一个不多于5位的正整数，要求：一、求它是几位数，二、逆序打印出各位数字。  
'''

def main(n):
    _list = []
    num = 0
    while n > 0:
        mod = n % 10
        _list.append(mod)
        n //= 10
        num += 1
    for i in _list:
        print(f"{i} ")

if __name__ == "__main__":
    main(12345)
