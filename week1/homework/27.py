'''
题目：求100之内的素数
'''

def is_prime(n) -> bool:
    if n < 2:
        return False
    elif n == 2:
        return True
    elif n % 2 == 0:
        return False

    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True

for i in range(100):
    if is_prime(i):
        print(f"{i} ")
