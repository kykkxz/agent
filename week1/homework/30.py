'''
题目：有一个已经排好序的数组。现输入一个数，要求按原来的规律将它插入数组中。  
1.   程序分析：首先判断此数是否大于最后一个数，然后再考虑插入中间的数的情况，插入后此元素之后的数，依次后移一个位置。  
'''

def insert_number():
    _list = [1, 4, 6, 9, 13, 16, 19, 28, 40, 100]
    print(f"原数组: {_list}")
    
    num = int(input("请输入要插入的数字:\n"))
    
    if num >= _list[-1]:
        _list.append(num)
    else:
        for i in range(len(_list)):
            if _list[i] > num:
                _list.insert(i, num)
                break 
                
    print(f"插入后的数组: {_list}")

if __name__ == "__main__":
    insert_number()
