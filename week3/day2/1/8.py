import os

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "exercise_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

iris = pd.read_csv(os.path.join(BASE_DIR, "Iris.csv"))
iris = iris.rename(
    columns={
        "SepalLengthCm": "sepal_length",
        "SepalWidthCm": "sepal_width",
        "PetalLengthCm": "petal_length",
        "PetalWidthCm": "petal_width",
        "Species": "species",
    }
)

subset = iris[["sepal_length", "sepal_width", "petal_length", "species"]]

sns.pairplot(subset, hue="species")
plt.savefig(os.path.join(OUTPUT_DIR, "exercise_08_iris_pairplot.png"))
plt.close()
