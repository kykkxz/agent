# 属性

power = 5
Intelliger = 10
Agile = 7
HP = 3
MP = 1

# 调试
print("力量", power)
print("HP", HP)
print("MP", MP)

# 加点
add_num = 0;


type_add = 0;

while True:
    type_add = input("请选择加点，0为退出，1=力量, 2=智力，3=敏捷\n")
    type_add = int(type_add)
    if type_add == 0:
        break
    
    add_num = input("请输入加点")
    add_num = int(add_num)

    if add_num >= 0 and add_num < 10:
        if type_add == 1:
            power += add_num
        elif type_add == 2:
            Intelliger += add_num
        elif type_add == 3:
            Agile += add_num
    else:
        print("只能进行0~10的加点")
        continue


# ...

# 职业判断

if power > 12:
    print("入门战士")
if Intelliger > 10:
    print("入门学徒")
if Agile > 8:
    print("入门猎人")
