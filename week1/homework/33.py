'''
题目：打印出杨辉三角形（要求打印出10行如下图）  
'''
import math

def print_pascal_triangle_math(rows):
    for n in range(rows):
        print(' ' * (rows - n), end='')
        
        for m in range(n + 1):
            num = math.comb(n, m)
            print(num, end=' ')
        print()

if __name__ == "__main__":
    print_pascal_triangle_math(10)
