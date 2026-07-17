'''
题目：求1+2!+3!+...+20!的和  
1.程序分析：此程序只是把累加变成了累乘。 
'''
import math
def sum_acc(n):
    return sum([math.factorial(i) for i in range(1, n + 1)])

if __name__ == "__main__":
    print(f"{sum_acc(20)}")
    

