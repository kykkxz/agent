'''
题目：打印出如下图案（菱形）
*  
***  
*****  
*******  
*****  
***
*
'''

def draw_diamond():
    for i in range(4):
        print('*' * (2 * i + 1))
        
    for i in range(3):
        print('*' * (5 - 2 * i))

if __name__ == "__main__":
    draw_diamond()
