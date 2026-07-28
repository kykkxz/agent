from pathlib import Path
from typing import cast

import pandas as pd
from pandas import DataFrame, Series


EVENT_TYPE_MAP = {
    "view": "view",
    "浏览": "view",
    "cart": "cart",
    "add_to_cart": "cart",
    "加购": "cart",
    "购物车": "cart",
    "purchase": "purchase",
    "buy": "purchase",
    "购买": "purchase",
    "下单": "purchase",
}


def normalize_event_type(value: object) -> str:
    event_type = str(value).strip().lower()
    return EVENT_TYPE_MAP.get(event_type, "view")


def fill_price_by_category_median(df: DataFrame) -> Series:
    prices = Series(pd.to_numeric(df["price"], errors="coerce"), index=df.index)
    categories = Series(df["category"], index=df.index)
    category_medians = prices.groupby(categories).transform("median")
    global_median = prices.median()
    return prices.fillna(category_medians).fillna(global_median)


def clean_ecommerce_data(df: DataFrame) -> DataFrame:
    cleaned = df.copy()

    cleaned["event_type"] = cleaned["event_type"].apply(normalize_event_type)
    cleaned["user_age"] = pd.to_numeric(cleaned["user_age"], errors="coerce")
    age = Series(cleaned["user_age"], index=cleaned.index)
    cleaned = cast(DataFrame, cleaned.loc[age.between(0, 100, inclusive="both")])

    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce")
    timestamp = Series(cleaned["timestamp"], index=cleaned.index)
    cleaned = cast(DataFrame, cleaned.loc[timestamp.notna()])

    cleaned = cast(DataFrame, cleaned.drop_duplicates())
    cleaned = cast(DataFrame, cleaned.sort_values(by=["user_id", "item_id", "timestamp"]))
    cleaned = cast(DataFrame, cleaned.drop_duplicates(
        subset=["user_id", "item_id", "event_type"],
        keep="last",
    ))

    cleaned["price"] = fill_price_by_category_median(cleaned)
    cleaned["device"] = cleaned["device"].astype(str).str.strip().str.lower()

    return cleaned.reset_index(drop=True)


def main() -> None:
    input_path = Path("ecommerce_dirty.csv")
    output_path = Path("ecommerce_clean.csv")

    df = pd.read_csv(input_path)
    cleaned = clean_ecommerce_data(df)
    cleaned.to_csv(output_path, index=False)

    print(f"清洗前记录数: {len(df)}")
    print(f"清洗后记录数: {len(cleaned)}")
    print(f"输出文件: {output_path}")
    print("\n清洗后数据预览:")
    print(cleaned.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
