# 0729 今日工作目标

- 监督学习回顾

- openrefine补充

- 无监督学习

- 项目一的核心pipeline：xgboost
  
  

## 模块0：回顾

1.资料推荐：

《机器学习》周志华（西瓜书）

《百面机器学习算法工程师带你面试》--面试专用

《《百面深度学习算法工程师带你面试》

《百面大模型算法工程师带你面试》

视频：吴恩达系列

![bc7faa1d-d3b8-4921-8caa-3500f775068b](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/bc7faa1d-d3b8-4921-8caa-3500f775068b.png)

2.特征工程-模型训练-模型预测-评估指标

模型导入：xgboost和lightgbm是单独的包，其他算法都从sklearn里面导入

特征工程：

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

X_test_scaled = scaler.transform(X_test)



model=模型名称(相关参数)

model.fit()



y_pred = model.predict(X_test_scaled)  #数值型输出

y_pred = model.predict(X_test_scaled)  #分类型输出的最终分类结果

y_prob = model.predict_proba(X_test_scaled)[:, 1] #分类型输出的可能性结果



mse = mean_squared_error(y_test, y_pred) #回归问题的评估指标

r2 = r2_score(y_test, y_pred)#回归问题的评估指标



分类问题的评估指标

1）混淆矩阵：有什么用？

 2）准确率，精准率，召回率，f1-score

classification_report(y_test, y_pred, target_names=['未流失', '流失'])  

![929d6ef6-3e22-4cab-87bb-0bef08709741](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/929d6ef6-3e22-4cab-87bb-0bef08709741.png)

3）AUC，PR-AUC

   # ROC曲线

    fpr, tpr, _ = roc_curve(y_test, y_prob)

    roc_auc = auc(fpr, tpr)





# 模块一：openrefine（数据清洗补充）

### 1.介绍：

可视化五代码工具，不用编写代码，清洗数据。

pandas功能一致，适合于做小规模单文件的数据处理和做数据清洗的demo，用以确定清洗策略，再在实际的批量数据中用pandas复现

问题在于：无法批量处理文件

### 2.核心功能

1）类型转换

![0101e5da-73e6-48b2-9c25-187c8f447374](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/0101e5da-73e6-48b2-9c25-187c8f447374.png)

2）数值聚类

![6317a993-758f-4060-80fd-3f3fb364a9e4](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/6317a993-758f-4060-80fd-3f3fb364a9e4.png)



![583e7ae0-7a8c-40cf-a12f-84bb9b8d02ba](file:///C:/Users/qiuxingyu/OneDrive/Pictures/Typedown/583e7ae0-7a8c-40cf-a12f-84bb9b8d02ba.png)



## 模块三：非监督学习：聚类算法

#### 1.理论讲解：

监督学习-有标签的：features-->y：数值or类别

非监督学习-无标签：features

聚类clustering：把相似的样本归到一组，不同的样本分到不同组，比如：

- 客户分群：把用户按消费行为分为几类，精准营销

- 异常检测：正常数据聚集成簇，离所有簇远的可能就是异常（网络安全攻击类/工业机器的使用情况）

- 图像分割：把图像按形状或者颜色，分割出不同区域

### 2.最常见的四种聚类算法：

- K-Means:K均值聚类--最常用最经典

- DBSCAN（基于密度的聚类）**

- 层次聚类**

- GMM（高斯混合模型）**

K-Means：核心思想-把数据分成k个簇，每个簇都有一个中心

步骤（迭代）：

```python
1. 随机选 K 个点作为初始中心
2. 每个样本归到离它最近的中心 → 形成K个簇
3. 重新计算每个簇的中心(所有点的平均)
4. 重复 2、3 步,直到中心不再变化(收敛)
```

    建议大家看一下视频（b站），直观图形介绍



**四种算法对比**:

| 算法      | 是否指定K | 簇形状          | 噪声处理   | 适用场景       |
| ------- | ----- | ------------ | ------ | ---------- |
| K-Means | 需要    | 仅球形          | 无      | 大数据、球形簇    |
| 层次聚类    | 需要    | 任意(看linkage) | 无      | 想看层次结构/树状图 |
| DBSCAN  | 不需要   | 任意形状         | 自动识别噪声 | 任意形状、含噪声   |
| GMM     | 需要    | 椭圆形          | 无      | 需要概率(软聚类)  |

不知道球形、形状不规则-->DBSCAN;

球形：K-Means

需要计算概率：GMM

想看层次：层次聚类（比如游戏公司的数据分析员，rmb vs 非rmb玩家，rmb玩家小r，中r，大r）



## 模块四：总览表










