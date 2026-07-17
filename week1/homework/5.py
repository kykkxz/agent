'''
题目：利用条件运算符的嵌套来完成此题：学习成绩> =90分的同学用A表示，60-89分之间的用B表示，60分以下的用C表示。  
1.程序分析：(a> b)?a:b这是条件运算符的基本例子。  
'''

if __name__ == "__main__":
    n = int(input("请输入成绩\n"))

    result = 'A' if n >= 90 else 'B' if 60 < n < 90 else 'C'

    print(f"{result}")
