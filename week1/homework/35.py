'''
题目：输入数组，最大的与第一个元素交换，最小的与最后一个元素交换，输出数组
'''


_list = list(map(int, input("请输入数组\n")))

max_val = max(_list)

max_idx = _list.index(max_val)

_list[0], _list[max_idx] = _list[max_idx], _list[0]

min_val = min(_list) 

min_idx = _list.index(min_val) 
    
_list[-1], _list[min_idx] = _list[min_idx], _list[-1]

print(f"交换后的数组: {_list}")
