# goods/milk_cap.py - 奶盖茶子类
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from goods.base_drink import BaseDrink


# 继承BaseDrink，实现奶盖茶专属优惠：购买2杯及以上立减3元
class MilkCapTea(BaseDrink):
# 实例属性，__milk_cap_cost 
    __milk_cap_cost = 0

    def __init__(self, name : str, price : float):
        super().__init__(name, price)

# get_milk_cap_cost()   -->获取奶盖的单杯价格
    def get_milk_cap_cost(self) -> float:
        return self.price

    def get_final_price(self, buy_num: int) -> float:
        result = self.get_milk_cap_cost() * buy_num * self.shop_discount
        if buy_num >= 3:
            return result - 3
        else:
            return result



#测试代码
if __name__ == "__main__":
    tea = MilkCapTea("奶茶", 5)
    print(tea.get_final_price(2))
