import os

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "exercise_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

tips = pd.read_csv(os.path.join(BASE_DIR, "tip.csv"))

sns.lmplot(data=tips, x="total_bill", y="tip", hue="smoker")
plt.title("账单与小费回归图（按吸烟情况对比）")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_07_reg_bill_tip_smoker.png"))
plt.close()
