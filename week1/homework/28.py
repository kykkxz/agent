'''
题目：求一个3*3矩阵对角线元素之和  
1.程序分析：利用双重for循环控制输入二维数组，再将a累加后输出。  
'''
def main():
    _matrix = []
    for i in range(3):
        row_str = input(f"输入第{i}行:\n")
        row_list = list(map(int, row_str.split()))
        _matrix.append(row_list)

    a = sum(_matrix[i][i] for i in range(3))

    print(f"{a}")
