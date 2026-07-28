from pathlib import Path

import numpy as np
import pandas as pd


class AutoDataCleaner:
    def __init__(self, df):
        self.df = df.copy()
        self.col_missing_drop_threshold = 0.5
        self.iqr_scale = 1.5

    def handle_missing_value(self):
        print("开始处理缺失值")
        cols_to_drop = []
        total_rows = len(self.df)

        for col in self.df.columns:
            missing_count = self.df[col].isna().sum()
            missing_rate = missing_count / total_rows if total_rows else 0
            print(f"{col} 缺失率: {missing_rate:.2%}")

            if missing_rate > self.col_missing_drop_threshold:
                cols_to_drop.append(col)
                print(f"{col} 缺失率过高，标记删除")
            elif pd.api.types.is_numeric_dtype(self.df[col]):
                median_value = self.df[col].median()
                self.df[col] = self.df[col].fillna(median_value)
                print(f"{col} 为数值列，使用中位数 {median_value} 填充")
            else:
                self.df[col] = self.df[col].fillna("未知/未填写")
                print(f"{col} 为文本/分类列，使用占位值填充")

        if cols_to_drop:
            self.df = self.df.drop(columns=cols_to_drop)
            print(f"批量删除列: {', '.join(cols_to_drop)}")
        else:
            print("无高缺失率列需要删除")

        return self.df

    def handle_outlier(self, mode="clip"):
        print("开始处理 IQR 异常值")

        if mode not in {"clip", "drop"}:
            raise ValueError('mode 只能是 "clip" 或 "drop"')

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - self.iqr_scale * iqr
            upper_bound = q3 + self.iqr_scale * iqr
            outlier_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
            outlier_count = outlier_mask.sum()

            print(
                f"{col} 下限: {lower_bound:.4f}, 上限: {upper_bound:.4f}, "
                f"异常数量: {outlier_count}"
            )

            if outlier_count == 0:
                continue

            if mode == "clip":
                self.df[col] = self.df[col].clip(lower=lower_bound, upper=upper_bound)
                print(f"{col} 已使用 clip 截断处理")
            else:
                self.df = self.df[~outlier_mask].copy()
                print(f"{col} 已删除包含异常值的行")

        return self.df

    def run_full_clean(self, outlier_mode="clip"):
        print("启动自动化数据清洗流水线")
        self.handle_missing_value()
        self.handle_outlier(mode=outlier_mode)
        print("自动化数据清洗流水线完成")
        return self.df


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    raw_path = base_dir / "raw_data" / "customer_chat_raw.csv"
    clean_dir = base_dir / "clean_data"
    output_path = clean_dir / "auto_clean_result.csv"

    raw_df = pd.read_csv(raw_path, encoding="utf-8-sig")
    cleaner = AutoDataCleaner(raw_df)
    clean_df = cleaner.run_full_clean(outlier_mode="clip")

    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"清洗结果已导出: {output_path}")
