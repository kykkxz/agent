'''
题目：输入两个正整数m和n，求其最大公约数和最小公倍数。  
1.程序分析：利用辗除法。  
'''
def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return abs(a)

def lcm(a, b):
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


def main():
    m = int(input("请输入m\n"))
    n = int(input("请输入n\n"))
    print(f"最大公约数：{gcd(m,n)}")
    print(f"最小公倍数：{lcm(m,n)}")


if __name__ == "__main__":
    main()
