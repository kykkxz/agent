# BERT 文本分类三次迭代记录

数据：Yelp Review 二分类；随机种子：42；训练/验证/测试规模：2000/500/500。
模型：`BertForSequenceClassification.from_pretrained("bert-base-uncased")`。
三次实验均从同一个预训练 BERT 重新初始化，验证集和测试集固定。

| 迭代 | learning_rate | epochs | batch | weight_decay | warmup | max_length | eval_loss | eval_f1 | test_loss | test_f1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 2e-05 | 1 | 16 | 0.0 | 0.0 | 128 | 0.2688 | 0.8847 | 0.2571 | 0.8980 |
| higher_lr_regularized | 3e-05 | 2 | 16 | 0.01 | 0.1 | 128 | 0.3047 | 0.8967 | 0.2551 | 0.9100 |
| longer_context | 2e-05 | 2 | 16 | 0.01 | 0.1 | 192 | 0.2502 | 0.9079 | 0.2357 | 0.9099 |

当前三次实验中验证集 F1 最优：`longer_context`（eval_f1=0.9079）。
记录生成时间：2026-08-04T19:25:02+08:00
