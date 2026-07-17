'''
题目：求0—7所能组成的奇数个数。  
1 3 5 7 
0 2 4 6
'''
def count_odd_numbers():
    total_sum = 0
    
    for i in range(1, 9):
        if i == 1:
            current_count = 4
        else:
            current_count = 4 * 6
            
            available_digits = 6
            for _ in range(i - 2):
                current_count *= available_digits
                available_digits -= 1
                
        print(f"{i}位数的奇数个数有: {current_count}")
        total_sum += current_count

    print(f"0-7能组成的无重复数字奇数总数: {total_sum}")

if __name__ == "__main__":
    count_odd_numbers()
