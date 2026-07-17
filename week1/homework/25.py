'''
题目：一个5位数，判断它是不是回文数。即12321是回文数，个位与万位相同，十位与千位相同。  
'''
def main(n):
    _list = []
    num = 0
    while n > 0:
        mod = n % 10
        _list.append(mod)
        n //= 10
        num += 1

    for i in range(num // 2):
        if _list[i] != _list[num - 1 - i]:
            print(f"NO")
            return
    print(f"YES")
        
if __name__ == "__main__":
    main(12321)
    main(12341)
