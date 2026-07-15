'''
# 作业：魔法技能加点器综合项目

## 任务

独立编写完整交互程序，实现角色属性加点、伤害计算、Buff 发放、文件存档、异常容错功能。

## 需要用到知识点

字典、函数多返回值、装饰器、lambda、生成器 yield、列表推导式、while 循环、if 分支、try 异常捕获、with 文件操作、json 存储、程序入口。

## 必须实现功能

1. 初始化力量、智力、敏捷角色字典；
2. 装饰器实现双倍伤害特效；
3. lambda 计算基础伤害；
4. 生成器产出魔法 Buff；
5. 列表推导式限制合法加点 0~10；
6. 加点函数判断点数合法性，返回结果；
7. 捕获非数字输入异常，程序不崩溃；
8. 菜单循环选择加点 / 退出，退出自动保存角色数据到本地文件；
9. 加点成功且点数大于 4 时领取 Buff，实时展示双倍技能伤害。

## 提交

提交.py 源码文件，独立手写代码，禁止抄袭。
自测：测试非法数字、超出范围点数、错误菜单序号、存档功能全部正常运行。
'''
import random
import json

Character = {"power": 0, "Intelliger": 0, "Agile": 0}

# 1.初始化
def initStatus():
    Character["power"] = random.randint(1, 10)
    Character["Intelliger"] = random.randint(1, 10)
    Character["Agile"] = random.randint(1, 10)
    return Character

# 2.双倍伤害
def double_damage(func):
    def wrapper(*args, **kwargs):
        orgin = func(*args, **kwargs)
        double = orgin * 2
        return double
    return wrapper

@double_damage
def attack(base_damage):
    return base_damage + random.randint(0,3)

# 3.lambda计算基础伤害
calc_base_damage = lambda: Character["power"] * 2 + Character["Intelliger"] + Character["Agile"] // 2

# 4.生成器buff
def magic_buff_generator():
    buffs = [
        "回血",
        "加攻击力"
    ]

    buff = random.choice(buffs)
    duration = random.randint(2,5)
    yield f"{buff}(持续{duration}秒)"

# 5.加点检查
def check_jd(num_add):
    if isinstance(num_add, int):
        valid_list = [x for x in [num_add] if 0 <= x <= 10]
        return num_add if 0 <= num_add <= 10 else None

    valid_list = [x for x in num_add if 0 <= x <= 10]   
    return valid_list[0] if valid_list else None


# 6/7.加点函数，捕获异常
def add_jd():
    try:
        num_add = input("请输入加点(0~10):")
        num_add = int(num_add)
        
        result = check_jd(num_add)

        if result is None:
            print("加点数必须在 0-10 之间！")
            return None
        return result

    except ValueError:
        print("请输入有效的数字")
        return None


# 8.菜单
def save_file(filename="character_data.json"):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(Character, f, ensure_ascii=False, indent=4)
        print(f"数据已保存到 {filename}")
        return True
    except Exception as e:
        print(f"保存失败: {e}")
        return False

def UI(Character):
    while True:
        print("\n" + "="*30)
        print(f"当前属性 -> 力量: {Character['power']}, 智力: {Character['Intelliger']}, 敏捷: {Character['Agile']}")
        print("请选择操作：0.退出并存档 | 1.加力量 | 2.加智力 | 3.加敏捷")
        print("="*30)
        
        type_id = input("选择菜单序号: ").strip()
        
        if type_id == "0":
            save_file()
            print("感谢使用，游戏退出！")
            break
            
        if type_id not in ["1", "2", "3"]:
            print("错误菜单序号，请重新选择！")
            continue
            
        num_jd = add_jd()
        if num_jd is None:
            continue  
            
        if type_id == "1":
            Character["power"] += num_jd
            print(f"力量成功增加了 {num_jd} 点！")
        elif type_id == "2":
            Character["Intelliger"] += num_jd
            print(f"智力成功增加了 {num_jd} 点！")
        elif type_id == "3":
            Character["Agile"] += num_jd
            print(f"敏捷成功增加了 {num_jd} 点！")
            
        if num_jd > 4:
            print("【触发特效】单次加点大于4点，成功触发魔法奇迹！")
            # 领用生成器Buff
            gen = magic_buff_generator()
            buff_info = next(gen)
            print(f"恭喜获得魔法Buff: {buff_info}")
            
            # 实时计算并展示伤害
            base_dmg = calc_base_damage()
            final_dmg = attack(base_dmg)
            print(f"基础伤害为: {base_dmg}")
            print(f"实时双倍爆发技能伤害: {final_dmg}点！")



def run():
    initStatus()
    UI(Character)
    return ;

if __name__ == "__main__":
    run()
