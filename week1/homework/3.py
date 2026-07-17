'''
题目：打印出所有的 "水仙花数 "，所谓 "水仙花数 "是指一个三位数，其各位数字立方和等于该数本身。例如：153是一个 "水仙花数 "，因为153=1的三次方＋5的三次方＋3的三次方。  
1.程序分析：利用for循环控制100-999个数，每个数分解出个位，十位，百位。
'''
def digits(n) -> list[int]:
    result = []
    if n == 0 :
        return [0]
    while n > 0:
        result.append(n % 10)
        n //= 10
    result.reverse()
    return result

def is_sxh(n) -> bool:
    dig = digits(n)
    
    sum = 0
    for i in dig:
        sum += i ** 3
     
    if sum == n:
        return True
    return False

def main():
    for i in range(100, 1000):
        if is_sxh(i):
            print(f"{i} ")

if __name__ == "__main__":
    main()
