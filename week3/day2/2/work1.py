import pandas as pd
from typing import Any
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score

# 1. 加载数据
housing : Any = fetch_california_housing()
X = pd.DataFrame(housing.data, columns=housing.feature_names)
y = pd.Series(housing.target, name="MedHouseVal")

# 探索性分析
print("数据形状:", X.shape)
print("\n特征统计描述:\n", X.describe())
print("\n目标变量统计描述:\n", y.describe())
print("\n特征与目标的相关系数:\n", X.corrwith(y).sort_values(ascending=False))

# 划分训练集/测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 2. 特征工程:标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 特征选择:选出与目标最相关的前6个特征
selector = SelectKBest(score_func=f_regression, k=6)
X_train_selected = selector.fit_transform(X_train_scaled, y_train)
X_test_selected = selector.transform(X_test_scaled)
selected_features = X.columns[selector.get_support()]
print("\n选中的特征:", list(selected_features))

# 3. 训练三种模型
models = {
    "线性回归": LinearRegression(),
    "决策树": DecisionTreeRegressor(random_state=42),
    "随机森林": RandomForestRegressor(n_estimators=100, random_state=42),
}

results = {}
for name, model in models.items():
    model.fit(X_train_selected, y_train)
    y_pred = model.predict(X_test_selected)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    results[name] = {"MSE": mse, "R2": r2}

# 4. 比较模型性能
print("\n模型性能比较:")
results_df = pd.DataFrame(results).T
print(results_df)

# 5. 特征重要性排序(以随机森林为例)
rf_model = models["随机森林"]
importance = pd.Series(rf_model.feature_importances_, index=selected_features)
importance = importance.sort_values(ascending=False)
print("\n随机森林特征重要性排序:\n", importance)
