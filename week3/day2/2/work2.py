from pathlib import Path

import matplotlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

matplotlib.rcParams["font.sans-serif"] = ["SimSun", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False



OUTPUT_DIR = Path(__file__).resolve().parent


np.random.seed(42)
n_samples = 1000

# 构造模拟客户特征与初始标签。
data = pd.DataFrame(
    {
        "年龄": np.random.randint(18, 65, n_samples),
        "月消费金额": np.random.exponential(200, n_samples),
        "使用时长_月": np.random.randint(1, 60, n_samples),
        "投诉次数": np.random.poisson(0.5, n_samples),
        "是否流失": np.zeros(n_samples, dtype=int),
    }
)
data["合约类型"] = np.random.choice(["月付", "年付"], size=n_samples, p=[0.65, 0.35])

# 用逻辑函数把客户特征映射为流失概率。
score = (
    -1.4
    + 0.025 * (data["年龄"] - 40)
    + 0.004 * (data["月消费金额"] - 200)
    - 0.045 * (data["使用时长_月"] - 24)
    + 0.85 * data["投诉次数"]
    + 0.65 * (data["合约类型"] == "月付").astype(int)
)
data["是否流失"] = np.random.binomial(1, 1 / (1 + np.exp(-score)))

numeric_features = ["年龄", "月消费金额", "使用时长_月", "投诉次数"]
categorical_features = ["合约类型"]
features = numeric_features + categorical_features
x = data[features]
y = data["是否流失"]

# 保持类别比例一致地划分训练集和测试集。
x_train, x_test, y_train, y_test = train_test_split(
    x,
    y,
    test_size=0.2,
    random_state=42, 
    stratify=y,
)

def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("标准化", StandardScaler(), numeric_features),
            ("独热编码", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

# 定义并比较三种常见分类模型。
models = {
    "逻辑回归": LogisticRegression(max_iter=1000, random_state=42),
    "SVM": CalibratedClassifierCV(SVC(random_state=42)), 
    "随机森林": RandomForestClassifier(n_estimators=100, random_state=42),
}

results = []
predictions = {}
scores = {}

print("========== 模拟客户数据 ==========")
print(data.head())
print(f"样本数: {len(data)}")
print(f"流失率: {y.mean():.2%}")
print(f"标准化数值特征: {', '.join(numeric_features)}")
print(f"独热编码类别特征: {', '.join(categorical_features)}")
print()

# 训练模型，记录预测结果和核心评估指标。
for model_name, model in models.items():
    pipeline = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            ("model", model),
        ]
    )
    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    y_score = pipeline.predict_proba(x_test)[:, 1]
    report = classification_report(
        y_test,
        y_pred,
        target_names=["未流失", "流失"],
        digits=4,
        output_dict=True,
    )
    roc_auc = roc_auc_score(y_test, y_score)

    predictions[model_name] = y_pred
    scores[model_name] = y_score
    results.append(
        {
            "模型": model_name,
            "准确率": report["accuracy"], # type: ignore[reportArgumentType]
            "流失类F1": report["流失"]["f1-score"], # type: ignore[reportArgumentType]
            "ROC-AUC": roc_auc,
        }
    )

    print(f"========== {model_name} ==========")
    print(classification_report(y_test, y_pred, target_names=["未流失", "流失"], digits=4))
    print("混淆矩阵:")
    print(confusion_matrix(y_test, y_pred))
    print(f"ROC-AUC: {roc_auc:.4f}")
    print()

# 保存各模型的混淆矩阵图。
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for axis, (model_name, y_pred) in zip(axes, predictions.items(), strict=True):
    ConfusionMatrixDisplay.from_predictions(
        y_test,
        y_pred,
        display_labels=["No Churn", "Churn"],
        cmap="Blues",
        ax=axis,
        colorbar=False,
    )
    axis.set_title(model_name)
fig.tight_layout()
confusion_path = OUTPUT_DIR / "work2_confusion_matrices.png"
fig.savefig(confusion_path, dpi=150)
plt.close(fig)

# 保存 ROC 曲线对比图。
fig, axis = plt.subplots(figsize=(7, 5))
for model_name, y_score in scores.items():
    RocCurveDisplay.from_predictions(y_test, y_score, name=model_name, ax=axis)
axis.plot([0, 1], [0, 1], "--", color="gray")
axis.set_title("ROC Curve")
fig.tight_layout()
roc_path = OUTPUT_DIR / "work2_roc_curve.png"
fig.savefig(roc_path, dpi=150)
plt.close(fig)

# 按 ROC-AUC 和流失类 F1 选择最佳模型。
metrics = pd.DataFrame(results).sort_values(
    by=["ROC-AUC", "流失类F1"],
    ascending=False,
)
best_model = metrics.iloc[0]["模型"]

print("========== 模型效果对比 ==========")
print(metrics.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
print()
print("========== 最佳模型分析 ==========")
print(f"最佳模型: {best_model}")
if best_model == "随机森林":
    print("随机森林能处理非线性关系和特征交互，因此在这组模拟数据上综合效果最好。")
elif best_model == "SVM":
    print("SVM 通过核函数刻画非线性边界，因此在标准化后的特征上表现最好。")
else:
    print("逻辑回归适合当前较接近线性的流失规律，模型简单且泛化稳定。")
print(f"混淆矩阵图片已保存: {confusion_path.name}")
print(f"ROC曲线已保存: {roc_path.name}")
