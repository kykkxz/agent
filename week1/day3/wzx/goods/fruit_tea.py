# goods/fruit_tea.py - 果茶子类
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from goods.base_drink import BaseDrink

# 继承BaseDrink，实现果茶专属优惠：全场折扣基础上额外95折
#重写打印小票方法：显示果茶专属优惠信息
class FruitTea(BaseDrink):
    def __init__(self, name: str, price: float):
        super().__init__(name, price)
        self.type = "果茶"

    def get_final_price(self, buy_num: int) -> float:
        print("果茶专属优惠：全场折扣基础上额外95折")
        origin = self.price * buy_num
        final = origin * self.shop_discount * 0.88
        return round(final, 2)

#测试代码

    
if __name__ == "__main__":
    tea = FruitTea("果茶", 5)
    print(tea.get_final_price(2))
