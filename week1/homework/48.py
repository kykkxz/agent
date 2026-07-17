'''
题目：某个公司采用公用电话传递数据，数据是四位的整数，在传递过程中是加密的，加密规则如下：每位数字都加上5,然后用和除以10的余数代替该数字，再将第一位和第四位交换，第二位和第三位交换。  
'''

def encrypt_data(password):
    password_list = [int(char) for char in str(password)]

    encrypted_list = [(num + 5) % 10 for num in password_list]

    result = int("".join(map(str, encrypted_list)))

    return result

if __name__ == "__main__":

    test_num = 1234
    print(f"原始数据: {test_num}")
    print(f"加密后的数据: {encrypt_data(test_num)}")
