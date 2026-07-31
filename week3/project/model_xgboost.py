#!/usr/bin/env uv run python3
# /// script
# dependencies = [
#     "numpy",
#     "pandas",
#     "scikit-learn",
#     "xgboost",
# ]
# ///
"""Train an XGBoost model from data_preprocessed.csv and write a txt report."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier


TARGET_COL = "Response"
HIGH_CARDINALITY_COLS = ("Region_Code", "Policy_Sales_Channel")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train XGBoost on preprocessed insurance response data and export a txt report."
    )
    parser.add_argument("--data-path", default="data_preprocessed.csv")
    parser.add_argument("--report-path", default="model_report.txt")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--n-estimators", type=int, default=300)
    return parser.parse_args()


def read_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"找不到输入文件: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    if TARGET_COL not in df.columns:
        raise ValueError(f"输入文件缺少目标列: {TARGET_COL}")
    return df


def stratified_sample(
    df: pd.DataFrame, sample_size: int | None, random_state: int
) -> pd.DataFrame:
    if sample_size is None or sample_size >= len(df):
        return df
    _, sampled = train_test_split(
        df,
        test_size=sample_size,
        stratify=df[TARGET_COL],
        random_state=random_state,
    )
    return sampled.reset_index(drop=True)


def add_frequency_encoding(
    train_df: pd.DataFrame, test_df: pd.DataFrame, columns: Iterable[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_out = train_df.copy()
    test_out = test_df.copy()
    for col in columns:
        if col not in train_out.columns:
            continue
        freq = train_out[col].value_counts(normalize=True)
        encoded_col = f"{col}_train_freq"
        train_out[encoded_col] = train_out[col].map(freq).fillna(0.0)
        test_out[encoded_col] = test_out[col].map(freq).fillna(0.0)
    return train_out, test_out


def add_target_encoding(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    columns: Iterable[str],
    random_state: int,
    n_splits: int = 5,
    smoothing: float = 20.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_out = train_df.copy()
    test_out = test_df.copy()
    global_mean = float(train_out[TARGET_COL].mean())
    splitter = StratifiedKFold(
        n_splits=n_splits, shuffle=True, random_state=random_state
    )

    for col in columns:
        if col not in train_out.columns:
            continue

        encoded_col = f"{col}_target_enc"
        train_out[encoded_col] = global_mean

        for train_idx, valid_idx in splitter.split(train_out, train_out[TARGET_COL]):
            fold_train = train_out.iloc[train_idx]
            stats = fold_train.groupby(col)[TARGET_COL].agg(["mean", "count"])
            smoothed = (
                stats["mean"] * stats["count"] + global_mean * smoothing
            ) / (stats["count"] + smoothing)
            train_out.iloc[
                valid_idx, train_out.columns.get_loc(encoded_col)
            ] = train_out.iloc[valid_idx][col].map(smoothed).fillna(global_mean)

        full_stats = train_out.groupby(col)[TARGET_COL].agg(["mean", "count"])
        full_smoothed = (
            full_stats["mean"] * full_stats["count"] + global_mean * smoothing
        ) / (full_stats["count"] + smoothing)
        test_out[encoded_col] = test_out[col].map(full_smoothed).fillna(global_mean)

    return train_out, test_out


def sanitize_columns(columns: Iterable[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for col in columns:
        safe = re.sub(r"[^0-9A-Za-z_]+", "_", str(col)).strip("_")
        if not safe:
            safe = "feature"
        if safe[0].isdigit():
            safe = f"f_{safe}"
        count = seen.get(safe, 0)
        seen[safe] = count + 1
        result.append(safe if count == 0 else f"{safe}_{count}")
    return result


def prepare_xy(
    train_df: pd.DataFrame, test_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    y_train = train_df[TARGET_COL].astype(int)
    y_test = test_df[TARGET_COL].astype(int)
    x_train = train_df.drop(columns=[TARGET_COL])
    x_test = test_df.drop(columns=[TARGET_COL])

    combined = pd.concat([x_train, x_test], axis=0, ignore_index=True)
    object_cols = [
        col
        for col in combined.columns
        if pd.api.types.is_object_dtype(combined[col].dtype)
        or pd.api.types.is_string_dtype(combined[col].dtype)
        or isinstance(combined[col].dtype, pd.CategoricalDtype)
    ]
    if object_cols:
        combined = pd.get_dummies(combined, columns=object_cols, drop_first=False, dtype=int)

    combined = combined.replace([np.inf, -np.inf], np.nan).fillna(0)
    combined = combined.astype(float)
    combined.columns = sanitize_columns(combined.columns)

    x_train_out = combined.iloc[: len(x_train)].reset_index(drop=True)
    x_test_out = combined.iloc[len(x_train) :].reset_index(drop=True)
    return x_train_out, y_train.reset_index(drop=True), x_test_out, y_test.reset_index(drop=True)


def build_model(
    y_train: pd.Series, n_estimators: int, random_state: int
) -> XGBClassifier:
    positive_count = int((y_train == 1).sum())
    negative_count = int((y_train == 0).sum())
    scale_pos_weight = negative_count / positive_count if positive_count else 1.0
    return XGBClassifier(
        n_estimators=n_estimators,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        reg_lambda=1.0,
        objective="binary:logistic",
        eval_metric="aucpr",
        tree_method="hist",
        n_jobs=-1,
        scale_pos_weight=scale_pos_weight,
        random_state=random_state,
    )


def threshold_metrics(y_true: pd.Series, probability: np.ndarray, threshold: float) -> dict[str, float]:
    prediction = (probability >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, prediction),
        "precision": precision_score(y_true, prediction, zero_division=0),
        "recall": recall_score(y_true, prediction, zero_division=0),
        "f1": f1_score(y_true, prediction, zero_division=0),
    }


def best_f1_threshold(y_true: pd.Series, probability: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, probability)
    if len(thresholds) == 0:
        return 0.5, 0.0
    f1_scores = 2 * precision[:-1] * recall[:-1] / (
        precision[:-1] + recall[:-1] + 1e-12
    )
    best_index = int(np.argmax(f1_scores))
    return float(thresholds[best_index]), float(f1_scores[best_index])


def top_feature_importance(model: XGBClassifier, limit: int = 20) -> list[tuple[str, float]]:
    booster = model.get_booster()
    scores = booster.get_score(importance_type="gain")
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]


def format_rate(value: float) -> str:
    return f"{value:.4f}"


def build_report(
    data_path: Path,
    df: pd.DataFrame,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    probability: np.ndarray,
    model: XGBClassifier,
    default_metrics: dict[str, float],
    best_threshold: float,
    best_threshold_metrics: dict[str, float],
) -> str:
    counts = df[TARGET_COL].value_counts().sort_index()
    negative_count = int(counts.get(0, 0))
    positive_count = int(counts.get(1, 0))
    imbalance_ratio = negative_count / positive_count if positive_count else float("inf")
    prediction_default = (probability >= 0.5).astype(int)
    matrix_default = confusion_matrix(y_test, prediction_default)
    auc = roc_auc_score(y_test, probability)
    pr_auc = average_precision_score(y_test, probability)
    importance_rows = top_feature_importance(model)

    lines = [
        "XGBoost 车险响应预测建模报告",
        "=" * 40,
        "",
        "一、数据与建模设置",
        f"- 输入文件: {data_path}",
        f"- 样本量: {len(df)}",
        f"- 原始特征列数: {df.shape[1] - 1}",
        f"- 模型训练特征数: {x_train.shape[1]}",
        f"- 训练集样本数: {len(x_train)}",
        f"- 测试集样本数: {len(x_test)}",
        f"- Response=0 数量: {negative_count}",
        f"- Response=1 数量: {positive_count}",
        f"- negative / positive 比例: {imbalance_ratio:.4f}",
        f"- XGBoost scale_pos_weight: {model.get_params()['scale_pos_weight']:.4f}",
        "",
        "二、可视化结论转特征工程",
        "- 无缺失值，因此不做缺失填补。",
        "- 特征间线性相关性极弱，因此保留非线性建模空间，不按相关系数删除核心字段。",
        "- Annual_Premium 极度右偏且长尾，使用原始值、截尾值、log 值和分箱特征共同表达。",
        "- Vehicle_Damage、Previously_Insured、Vehicle_Age 为强业务特征，并构造未投保、车辆受损、车龄较长的交叉特征。",
        "- Region_Code 与 Policy_Sales_Channel 具有明显响应率差异，建模阶段增加训练集频率编码和 K 折目标编码。",
        "- 类别不平衡通过 XGBoost 的 scale_pos_weight 处理。",
        "",
        "三、测试集统计指标",
        f"- ROC-AUC: {format_rate(auc)}",
        f"- PR-AUC / Average Precision: {format_rate(pr_auc)}",
        "",
        "默认阈值 0.50:",
        f"- Accuracy: {format_rate(default_metrics['accuracy'])}",
        f"- Precision: {format_rate(default_metrics['precision'])}",
        f"- Recall: {format_rate(default_metrics['recall'])}",
        f"- F1: {format_rate(default_metrics['f1'])}",
        "",
        f"F1 诊断最优阈值 {best_threshold:.4f}:",
        f"- Accuracy: {format_rate(best_threshold_metrics['accuracy'])}",
        f"- Precision: {format_rate(best_threshold_metrics['precision'])}",
        f"- Recall: {format_rate(best_threshold_metrics['recall'])}",
        f"- F1: {format_rate(best_threshold_metrics['f1'])}",
        "",
        "四、默认阈值混淆矩阵",
        f"- TN: {int(matrix_default[0, 0])}",
        f"- FP: {int(matrix_default[0, 1])}",
        f"- FN: {int(matrix_default[1, 0])}",
        f"- TP: {int(matrix_default[1, 1])}",
        "",
        "五、分类报告（默认阈值 0.50）",
        classification_report(y_test, prediction_default, digits=4, zero_division=0),
        "",
        "六、Top 20 特征重要性（gain）",
    ]

    for rank, (name, gain) in enumerate(importance_rows, start=1):
        lines.append(f"{rank:02d}. {name}: {gain:.6f}")

    lines.extend(
        [
            "",
            "七、建模建议",
            "- 当前任务建议优先关注 PR-AUC、Recall 和 F1，而不是只看 Accuracy。",
            "- 如果业务目标是尽量找到潜在购买客户，可适当降低阈值提高 Recall。",
            "- 如果业务目标是减少营销打扰，可适当提高阈值提高 Precision。",
            "- 目标编码已在训练集内做 K 折处理，避免直接使用全量标签导致数据泄露。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    data_path = Path(args.data_path)
    report_path = Path(args.report_path)

    df = read_data(data_path)
    df = stratified_sample(df, args.sample_size, args.random_state)

    train_df, test_df = train_test_split(
        df,
        test_size=args.test_size,
        stratify=df[TARGET_COL],
        random_state=args.random_state,
    )
    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    train_df, test_df = add_frequency_encoding(
        train_df, test_df, HIGH_CARDINALITY_COLS
    )
    train_df, test_df = add_target_encoding(
        train_df, test_df, HIGH_CARDINALITY_COLS, args.random_state
    )
    x_train, y_train, x_test, y_test = prepare_xy(train_df, test_df)

    model = build_model(y_train, args.n_estimators, args.random_state)
    model.fit(x_train, y_train)

    probability = model.predict_proba(x_test)[:, 1]
    default_metrics = threshold_metrics(y_test, probability, 0.5)
    best_threshold, _ = best_f1_threshold(y_test, probability)
    best_threshold_metrics = threshold_metrics(y_test, probability, best_threshold)
    report = build_report(
        data_path,
        df,
        x_train,
        x_test,
        y_train,
        y_test,
        probability,
        model,
        default_metrics,
        best_threshold,
        best_threshold_metrics,
    )

    report_path.write_text(report, encoding="utf-8")
    print(f"建模完成，报告已保存至: {report_path}")


if __name__ == "__main__":
    main()
