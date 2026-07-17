'''
题目：判断101-200之间有多少个素数，并输出所有素数。  
1.程序分析：判断素数的方法：用一个数分别去除2到sqrt(这个数)，如果能被整除，  
则表明此数不是素数，反之是素数。  
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
        
def main():
    num = 0
    for n in range(101, 201):
        if is_prime(n):
           num += 1
           print(f"{n} ")

if __name__ == "__main__":
    main()
