from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np

# 初始化 HuggingFaceEmbeddings，使用 bge-small-zh-v1.5 模型
embeddings_model = HuggingFaceEmbeddings(
    model_name="./bge-small-zh-v1.5",
    model_kwargs={'device': 'cuda'},
    encode_kwargs={'normalize_embeddings': False}
)

# 定义5个句子
sentences = [
    "Java开发工程师要求3年以上经验",
    "Python岗位要求熟悉Django框架",
    "公司节日福利包括购物卡和电影票",
    "员工享受带薪年假和五险一金",
    "Java高级工程师需精通JVM调优"
]

# 编码句子
embeddings = embeddings_model.embed_documents(sentences)

# 转换为 numpy 数组方便查看
embeddings_array = np.array(embeddings)

# 输出向量维度
print(f"向量维度: {embeddings_array.shape[1]}\n")

# 输出每个句子的前5个数值
for i, sentence in enumerate(sentences):
    print(f"句子 {i+1}: {sentence}")
    print(f"前5个数值: {embeddings_array[i][:5].tolist()}")
    print()

# 计算余弦相似度矩阵
similarity_matrix = np.dot(embeddings_array, embeddings_array.T)

# 输出相似度矩阵
print("=" * 60)
print("相似度矩阵 (5x5)")
print("=" * 60)
print("\n句子索引: 0=Java开发工程师要求3年以上经验")
print("          1=Python岗位要求熟悉Django框架")
print("          2=公司节日福利包括购物卡和电影票")
print("          3=员工享受带薪年假和五险一金")
print("          4=Java高级工程师需精通JVM调优")
print("\n")

# 格式化输出矩阵
print("        0      1      2      3      4")
print("-" * 45)
for i in range(5):
    row = f"{i}  "
    for j in range(5):
        row += f"{similarity_matrix[i][j]:.4f} "
    print(row)

# 找出最相似的句子对（排除自身）
print("\n" + "=" * 60)
print("详细相似度分析")
print("=" * 60)

max_similarity = -1
max_pair = None

# 遍历所有组合
for i in range(5):
    for j in range(i+1, 5):  # 只考虑上三角，避免重复
        sim = similarity_matrix[i][j]
        print(f"句子 {i} vs 句子 {j}: {sim:.4f}")
        
        if sim > max_similarity:
            max_similarity = sim
            max_pair = (i, j)

# 输出最相似的句子对
print("\n" + "=" * 60)
print("结果分析")
print("=" * 60)
print(f"\n✅ 最相似的句子对: 句子 {max_pair[0]} 和 句子 {max_pair[1]}")
print(f"   余弦相似度: {max_similarity:.4f}")
print(f"\n   句子 {max_pair[0]}: {sentences[max_pair[0]]}")
print(f"   句子 {max_pair[1]}: {sentences[max_pair[1]]}")


print("\n" + "=" * 60)
print("用户提问查询")
print("=" * 60)

# 用户提问
user_query = "Java岗位有什么要求？"
print(f"\n📝 用户提问: {user_query}")

# 编码用户提问
query_embedding = embeddings_model.embed_query(user_query)
query_embedding_array = np.array(query_embedding)

# 计算用户提问与所有句子的相似度
query_similarities = np.dot(embeddings_array, query_embedding_array)

# 输出所有句子的相似度
print("\n各句子与提问的相似度:")
print("-" * 50)
for i, sentence in enumerate(sentences):
    print(f"句子 {i} ({sentence[:20]}...): {query_similarities[i]:.4f}")

# 找出Top 2最相似的句子
top_k = 2
top_indices = np.argsort(query_similarities)[::-1][:top_k]  # 降序排列取前k个

print("\n" + "=" * 60)
print(f"Top {top_k} 最相似结果")
print("=" * 60)

for rank, idx in enumerate(top_indices, 1):
    print(f"\n🏆 Top {rank}:")
    print(f"   句子索引: {idx}")
    print(f"   完整句子: {sentences[idx]}")
    print(f"   相似度得分: {query_similarities[idx]:.4f}")

# 添加语义分析
print("\n" + "=" * 60)
print("语义分析")
print("=" * 60)

# 找出最低相似度（完全不相关的）
min_idx = np.argmin(query_similarities)
print(f"\n💡 最不相关的句子 (相似度最低):")
print(f"   句子 {min_idx}: {sentences[min_idx]}")
print(f"   相似度: {query_similarities[min_idx]:.4f}")

# 判断是否有相关结果
if query_similarities[top_indices[0]] > 0.5:
    print(f"\n✅ 找到高度相关的结果！")
else:
    print(f"\n⚠️  相似度较低，可能没有直接匹配的答案")