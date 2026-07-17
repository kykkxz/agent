'''
题目：输入3个数a,b,c，按大小顺序输出。  
1.程序分析：利用指针方法。 
'''
_list = sorted(list(map(int, input("请输入三个数\n"))))

for i in _list:
    print(f"{i}", end=' ')
