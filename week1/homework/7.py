'''
题目：输入一行字符，分别统计出其中英文字母、空格、数字和其它字符的个数。  
1.程序分析：利用while语句,条件为输入的字符不为 '\n '.  
'''

def statistics(string : str):
    letters = 0 
    spaces = 0
    digits = 0
    others = 0

    i = 0
    while i < len(string):
        c = string[i]

        if c.isalpha():
            letters += 1
        elif c == " ":
            spaces += 1
        elif c.isdigit():
            digits += 1
        else:
            others += 1

        i += 1

    return {'letter' : letters, 'spaces' : spaces, 'digits' : digits, 'others' : others}

def main():
    c = input("请输入:\n")

    cdict = statistics(c)

    for k, v in cdict.items():
        print(f"{k}:{v} ")


if __name__ == "__main__":
    main()
