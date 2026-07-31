import pandas as pd
import numpy as np

#读取文件
df = pd.read_excel("data.xlsx")

response_target = df["Response"].copy() if "Response" in df.columns else None

# 1.age 年龄和目标可能不是线性关系，分箱可以帮助模型捕捉不同年龄段的转化差异。
df["age_bin"] = pd.cut(
        df["Age"],
        bins = [0, 24, 34, 44, 54, 64, 100],
        labels=["<=24", "25-34", "35-44", "45-54", "55-64", "65+"]
    )
df["is_young"] = (df["Age"] < 30).astype(int)
df["is_middle_Age"] = ((df["Age"] >= 30) & (df["Age"] <= 49)).astype(int)
df["is_senior"] = (df["Age"] >= 50).astype(int)


# 2.Annual_Premium,年保费极度右偏、长尾、离群值多，这是重点处理对象
df["annual_premium_raw"] = df["Annual_Premium"]

# 截尾，减少极端值影响
lower = df["Annual_Premium"].quantile(0.01)
upper = df["Annual_Premium"].quantile(0.99)
df["annual_premium_clip"] = df["Annual_Premium"].clip(lower, upper)

# log 变换，缓解右偏
df["annual_premium_log"] = np.log1p(df["Annual_Premium"])

# 保费分箱
df["premium_bin"] = pd.qcut(
        df["Annual_Premium"],
        q=5,
        labels=["very_low", "low", "medium", "high", "very_high"],
        duplicates="drop"
    )

# 3. Vintage, 客户资历均匀分布

df["vintage_bin"] = pd.cut(
        df["Vintage"],
        bins=[0, 60, 120, 180, 240, 300],
        labels=["0-60", "61-120", "121-180", "181-240", "241-300"]
)

df["is_new_customer"] = (df["Vintage"] <= 60).astype(int)
df["is_old_customer"] = (df["Vintage"] >= 240).astype(int)

# 4. Vehicle_Age,车龄越长，购买意愿越强，尤其 > 2 Years 转化比例高
vehicle_age_map = {
      "< 1 Year": 0,
      "1-2 Year": 1,
      "> 2 Years": 2
  }

df["vehicle_age_ord"] = df["Vehicle_Age"].map(vehicle_age_map)# type: ignore[reportArgumentType] 
df["vehicle_age_gt_1"] = (df["vehicle_age_ord"] >= 1).astype(int)
df["vehicle_age_gt_2"] = (df["Vehicle_Age"] == "> 2 Years").astype(int)

# 5. vehicle_damage, 这是强特征，必须保留。
df["vehicle_damage_yes"] = (df["Vehicle_Damage"] == "Yes").astype(int)

# 6. Previously_Insured  也是强特征，必须保留。
df["previously_insured"] = df["Previously_Insured"].astype(int)
df["not_previously_insured"] = (df["Previously_Insured"] == 0).astype(int)

# 7. Gender  性别有一定差异，但不是强特征，简单编码即可
df["gender_male"] = (df["Gender"] == "Male").astype(int)

# 8. Driving_License 这是低方差特征，绝大多数都是 1
df["driving_license"] = df["Driving_License"].astype(int)

# 9. 未投保的人更可能响应 车辆受损的人更可能响应 车龄越长购买意愿越强,  所以应该构造这些交叉特征
df["not_insured_and_damaged"] = (
  (df["Previously_Insured"] == 0) &
  (df["Vehicle_Damage"] == "Yes")
).astype(int)

df["not_insured_and_vehicle_old"] = (
  (df["Previously_Insured"] == 0) &
  (df["vehicle_age_ord"] >= 1)
).astype(int)

df["damaged_and_vehicle_old"] = (
  (df["Vehicle_Damage"] == "Yes") &
  (df["vehicle_age_ord"] >= 1)
).astype(int)

# 未投保 + 车辆受损 + 车龄超过 1 年, 这类客户很可能是高购买意向人群。
df["core_high_intent_user"] = (
  (df["Previously_Insured"] == 0) &
  (df["Vehicle_Damage"] == "Yes") &
  (df["vehicle_age_ord"] >= 1)
).astype(int)

# 10. Region_Code 地区 28 数量最大，响应率也最高,地区 18、3、35、41、29 响应率也较高,地区字段是高基数类别
high_response_regions = [28, 18, 3, 35, 41, 29]

df["is_region_28"] = (df["Region_Code"] == 28).astype(int)
df["is_high_response_region"] = df["Region_Code"].isin(high_response_regions).astype(int)

region_freq = df["Region_Code"].value_counts(normalize=True)
df["region_freq"] = df["Region_Code"].map(region_freq) # type: ignore[reportArgumentType]

# 11. Policy_Sales_Channel明显的“高量低效”和“低量高效”
## 构造特征
low_efficiency_channels = [152, 160]
high_efficiency_channels = [155, 163, 157, 154, 156]
balanced_good_channels = [25, 26, 124]

## 频率编码
df["is_low_efficiency_channel"] = df["Policy_Sales_Channel"].isin(low_efficiency_channels).astype(int)
df["is_high_efficiency_channel"] = df["Policy_Sales_Channel"].isin(high_efficiency_channels).astype(int)
df["is_balanced_good_channel"] = df["Policy_Sales_Channel"].isin(balanced_good_channels).astype(int)

# 12. 渠道和用户状态交叉特征

df["high_channel_and_damaged"] = (
  df["is_high_efficiency_channel"] &
  df["vehicle_damage_yes"]
).astype(int)

df["good_channel_and_not_insured"] = (
  df["is_balanced_good_channel"] &
  df["not_previously_insured"]
).astype(int)

df["region28_and_damaged"] = (
  df["is_region_28"] &
  df["vehicle_damage_yes"]
).astype(int)

df["high_region_and_core_user"] = (
  df["is_high_response_region"] &
  df["core_high_intent_user"]
).astype(int)

# 13.1 执行独热编码 (One-Hot Encoding)
one_hot_cols = [
  "age_bin",
  "premium_bin",
  "vintage_bin"
]
df = pd.get_dummies(df, columns=one_hot_cols, drop_first=False, dtype=int)

# 13.2 清理已完成编码的原始文本/冗余列及 id
cols_to_drop = [
    "id",
    "gender",
    "Vehicle_Age",
    "Vehicle_Damage",
    "Response"
]
existing_drop_cols = [col for col in cols_to_drop if col in df.columns]
df_cleaned = df.drop(columns=existing_drop_cols)

# 13.3 重新把目标变量 Response 追加到最后一列（方便模型读取）
if response_target is not None:
    df_cleaned["Response"] = response_target

# 14. 输出预处理后的最终 CSV 文件
output_path = "data_preprocessed.csv"
df_cleaned.to_csv(output_path, index=False, encoding="utf-8-sig")

print(
    f"预处理完成！最终数据形状: {df_cleaned.shape}，已成功导出至 '{output_path}'"
)
