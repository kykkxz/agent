'''
题目：古典问题：有一对兔子，从出生后第3个月起每个月都生一对兔子，小兔子长到第三个月后每个月又生一对兔子，假如兔子都不死，问每个月的兔子总数为多少？  
1.程序分析： 兔子的规律为数列1,1,2,3,5,8,13,21....  
'''
def main():
    n = input("请输入月份\n")
    n = int(n)
    if n < 0:
      raise ValueError("n must be non-negative")

    a, b = 0, 1
    for _ in range(n):
      a, b = b, a + b
    
    print(f"{n}月一共有{a}兔子")

if __name__ == "__main__":
    main()
