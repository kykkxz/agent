'''
题目：输入某年某月某日，判断这一天是这一年的第几天？  
1.程序分析：以3月5日为例，应该先把前两个月的加起来，然后再加上5天即本年的第几天，特殊情况，闰年且输入月份大于3时需考虑多加一天。 
'''

from datetime import datetime

def datetime_way():
    data = input("请输入日期 (如 2026-3-5):\n")
    date_obj = datetime.strptime(data, "%Y-%m-%d")
    
    day_of_year = date_obj.strftime("%j")
    
    print(f"这一天是这一年的第 {int(day_of_year)} 天")

if __name__ == "__main__":
    datetime_way()
