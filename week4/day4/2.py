import json
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ORDER_DB = {
    "1001": {"status": "已发货", "item": "Python编程入门", "date": "2026-08-01"},
    "1002": {"status": "运输中", "item": "LangChain实战教程", "date": "2026-08-03"},
    "1003": {"status": "已签收", "item": "AI智能体开发指南", "date": "2026-07-25"},
}

@tool
def query_order(order_id: str) -> str:
    """查询订单状态"""
    print(f"[工具调用] query_order(order_id={order_id})")
    order = ORDER_DB.get(str(order_id))
    if order is None:
        return json.dumps({"message": "未查询到该订单"}, ensure_ascii=False)
    return json.dumps(
        {"order_id": str(order_id), **order},
        ensure_ascii=False,
    )

@tool
def calculate_refund(
    original_price: float,
    discount: float,
    days_since_purchase: int,
) -> str:
    """计算退款金额"""
    print(
        f"[工具调用] calculate_refund(original_price={original_price}, "
        f"discount={discount}, days_since_purchase={days_since_purchase})"
    )
    actual_paid = original_price * discount
    if days_since_purchase <= 7:
        refund = actual_paid
        reason = "7天无理由退货，全额退款"
    elif days_since_purchase <= 30:
        refund = actual_paid * 0.8
        reason = "7-30天退货，扣除20%手续费"
    else:
        return "购买已超过30天，不支持退货"

    return json.dumps(
        {
            "original_price": original_price,
            "actual_paid": round(actual_paid, 2),
            "refund": round(refund, 2),
            "reason": reason,
        },
        ensure_ascii=False,
    )

@tool
def recommend_product(category: str, budget: float) -> str:
    """根据品类和预算推荐商品"""
    print(f"[工具调用] recommend_product(category={category}, budget={budget})")
    products = {
        "编程书": [
            {"name": "Python入门", "price": 59},
            {"name": "LangChain实战", "price": 89},
        ],
        "AI书": [
            {"name": "智能体开发", "price": 129},
            {"name": "大模型原理", "price": 99},
        ],
        "工具书": [
            {"name": "Git实战", "price": 49},
            {"name": "Docker入门", "price": 69},
        ],
    }
    recommendations = [
        product
        for product in products.get(category, [])
        if product["price"] <= budget
    ]
    recommendations.sort(key=lambda product: product["price"])
    return json.dumps(
        {
            "category": category,
            "budget": budget,
            "products": recommendations,
        },
        ensure_ascii=False,
    )


@tool
def check_coupon(product_price: float) -> str:
    """计算最优优惠券组合"""
    print(f"[工具调用] check_coupon(product_price={product_price})")
    coupons = []
    if product_price >= 100:
        coupons.append("满100减10")
    if product_price >= 200:
        coupons.append("满200减30")
    if product_price >= 500:
        coupons.append("满500减80")

    discount_amount = sum(
        discount
        for threshold, discount in ((100, 10), (200, 30), (500, 80))
        if product_price >= threshold
    )
    return json.dumps(
        {
            "product_price": product_price,
            "coupons": coupons,
            "discount_amount": discount_amount,
            "final_price": round(product_price - discount_amount, 2),
        },
        ensure_ascii=False,
    )

@tool
def get_shipping_fee(city: str) -> str:
    """计算运费"""
    print(f"[工具调用] get_shipping_fee(city={city})")
    if "北京" in city or "上海" in city:
        base = 5
    elif "省" in city or "市" in city:
        base = 8
    else:
        base = 12
    return json.dumps(
        {"city": city, "shipping_fee": base},
        ensure_ascii=False,
    )


llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),#type: ignore[reportArgumentType]
    api_key=os.getenv("API_KEY"),#type: ignore[reportArgumentType]
    base_url=os.getenv("BASE_URL"),
    temperature=0.3,
)

tools = [
    query_order,
    calculate_refund,
    recommend_product,
    check_coupon,
    get_shipping_fee,
]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=(
        "你是一个专业的电商平台智能客服。请根据用户问题选择合适的工具，"
        "涉及订单、退款、商品、优惠券和运费时必须调用工具，并用中文清晰回答。"
        "涉及到有关订单优惠的问题，可以尝试对商品经行组合购买来确认优惠"
    ),
)


if __name__ == "__main__":
    print("电商智能客服已启动，输入 exit 退出。")
    messages = []

    while True:
        question = input("用户：").strip()
        if question.lower() == "exit":
            break

        messages.append(("user", question))
        result = agent.invoke({"messages": messages})
        messages = result["messages"]
        print(f"客服：{messages[-1].content}")
