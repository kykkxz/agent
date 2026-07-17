'''
题目：将一个正整数分解质因数。例如：输入90,打印出90=2*3*3*5。  
程序分析：对n进行分解质因数，应先找到一个最小的质数k，然后按下述步骤完成：  
(1)如果这个质数恰等于n，则说明分解质因数的过程已经结束，打印出即可。  
(2)如果n <> k，但n能被k整除，则应打印出k的值，并用n除以k的商,作为新的正整数你n,重复执行第一步。  
(3)如果n不能被k整除，则用k+1作为k的值,重复执行第一步。 
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

def split_factor(n):
    factors = []

    while n % 2 == 0:
        factors.append(2)
        n //= 2

    factor = 3
    while factor * factor <= n:
        while n % factor == 0:
            factors.append(factor)
            n //= factor
        factor += 2

    if n > 1:
        factors.append(n)

    return factors


def main(n):
    if n < 2:
        print("请输入大于1的正整数")
    elif is_prime(n):
        print(f"{n}就是质数")
    else:
        factors = split_factor(n)
        print(f"{n} = {' * '.join(map(str, factors))}")

if __name__ == "__main__":
    n = int(input("请输入n\n"))
    main(n)
