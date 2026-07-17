'''
题目：一个偶数总能表示为两个素数之和。
'''

def is_prime(num: int) -> bool:
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True

def verify_goldbach(n: int):
    if n <= 2 or n % 2 != 0:
        print("请输入一个大于 2 的偶数:\n")
        return

    for i in range(2, n // 2 + 1):
        if is_prime(i) and is_prime(n - i):
            print(f"验证成功: 偶数 {n} = 质数 {i} + 质数 {n - i}")
            return 

if __name__ == "__main__":
    verify_goldbach(100)
    verify_goldbach(2026)  
