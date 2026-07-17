'''
题目：请输入星期几的第一个字母来判断一下是星期几，如果第一个字母一样，则继续   判断第二个字母。  
1.程序分析：用情况语句比较好，如果第一个字母一样，则判断用情况语句或if语句判断第二个字母。  
'''
def check_weekday():
    first = input("请输入星期几的第一个字母:\n").upper().strip()
    
    if first == 'M':
        print("这是 Monday (星期一)")
    elif first == 'W':
        print("这是 Wednesday (星期三)")
    elif first == 'F':
        print("这是 Friday (星期五)")
        
    elif first == 'T':
        print("首字母是 T 无法确定，请输入第二个字母:")
        second = input().lower().strip()
        if second == 'u':
            print("这是 Tuesday (星期二)")
        elif second == 'h':
            print("这是 Thursday (星期四)")
        else:
            print("输入有误，无法匹配！")
            
    elif first == 'S':
        print("首字母是 S 无法确定，请输入第二个字母:")
        second = input().lower().strip()
        if second == 'a':
            print("这是 Saturday (星期六)")
        elif second == 'u':
            print("这是 Sunday (星期日)")
        else:
            print("输入有误，无法匹配！")
            
    else:
        print("无效的首字母，请输入 M, T, W, F, S 中的一个。")

if __name__ == "__main__":
    check_weekday()
