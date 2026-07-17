'''
题目：一个数如果恰好等于它的因子之和，这个数就称为 "完数 "。例如6=1＋2＋3.编程   找出1000以内的所有完数。  
'''

def find_factor(n):
    if n <= 1:
        return []
    i = 1
    list = []
    while i * i <= n:
        if n % i == 0:
            if i == 1:
                list.append(i)
            else:
                list.append(i)
                if i * i != n:
                    list.append(n // i)
        i += 1
    return list

def main():
    for i in range(1000):
        list = find_factor(i)
        sum = 0
        for j in list:
            sum += j
        if i == sum:
            print(f"{i} ")

if __name__ == "__main__":
    main()
