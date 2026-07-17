'''
题目：两个乒乓球队进行比赛，各出三人。甲队为a,b,c三人，乙队为x,y,z三人。已抽签决定比赛名单。有人向队员打听比赛的名单。a说他不和x比，c说他不和x,z比，请编程序找出三队赛手的名单。  
'''

import itertools

def find_opponents_elegant():
    for p in itertools.permutations(['x', 'y', 'z']):
        if p[0] != 'x' and p[2] != 'x' and p[2] != 'z':
            print(f"a ─── {p[0]}")
            print(f"b ─── {p[1]}")
            print(f"c ─── {p[2]}")
            break

if __name__ == "__main__":
    find_opponents_elegant()
