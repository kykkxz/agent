'''
题目：有n个人围成一圈，顺序排号。从第一个人开始报数（从1到3报数），凡报到3的人退出圈子，问最后留下的是原来第几号的那位。  
'''

def main(total_people):
    person = list(range(1, len(total_people) + 1))

    count = 0

    while len(person) > 1:
        p = person.pop(0)
        count += 1

        if count == 3:
            count = 0
        else:
            person.append(p)

    return person[0]

if __name__ == "__main__":
    survivor = main(30)
    print(f"最后留下来的是原本的: {survivor} 号")
