'''
题目：有n个整数，使其前面各数顺序向后移m个位置，最后m个数变成最前面的m个数  
'''

def main(_list : list, m):
    n = len(_list)
    if n == 0:
        return _list

    m = m % n
    if m == 0:
        return _list

    result = _list[-m:] + _list[:-m]
    
    return result

if __name__ == "__main__":
    numbers = [1, 2, 3, 4, 5, 6, 7]
    m_steps = 3
    
    print(f"原数组: {numbers}")
    shifted = main(numbers, m_steps)
    print(f"向后移 {m_steps} 个位置后: {shifted}")

