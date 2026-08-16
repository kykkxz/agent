from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
import shutil
from datetime import datetime, timedelta

# 清理旧数据以便测试
if os.path.exists("./chroma_db_weight"):
    shutil.rmtree("./chroma_db_weight")

# 步骤1：初始化Embedding模型（使用本地模型）
embedding_model = HuggingFaceEmbeddings(
    model_name="D:/网讯/讲师内容/提升班课_0407起/第九周rag原理及实战/rag/bge-small-zh-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# 步骤2：构造不同时间和权限等级的文本块（Chunks）
# 注意：为了体现效果，我们构造了不同时间跨度的文档
today = datetime.now()
recent_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")       # 近 3 个月
old_date = (today - timedelta(days=400)).strftime("%Y-%m-%d")         # 超过 1 年
normal_date = (today - timedelta(days=200)).strftime("%Y-%m-%d")      # 中间时间段

docs_data = [
    {
        "text": "2025版Java工程师要求：熟练掌握Spring Boot、MySQL，3年以上经验。",
        "metadata": {"recency": recent_date, "authorization": "public"}
    },
    {
        "text": "2023版Python岗位要求：熟悉Django框架，掌握数据分析库，本科。",
        "metadata": {"recency": old_date, "authorization": "public"}
    },
    {
        "text": "内部机密：Java高级架构师（P8）职级标准，精通JVM调优。",
        "metadata": {"recency": recent_date, "authorization": "internal"}
    },
    {
        "text": "旧版福利制度：员工中秋节发放300元购物卡（已废止）。",
        "metadata": {"recency": old_date, "authorization": "internal"}
    },
    {
        "text": "近期通知：公司内部开展Java高级技术培训，全员参加。",
        "metadata": {"recency": normal_date, "authorization": "internal"}
    }
]

texts = [doc["text"] for doc in docs_data]
metadatas = [doc["metadata"] for doc in docs_data]

# 步骤3：存入Chroma向量库
vector_db = Chroma.from_texts(
    texts=texts,
    embedding=embedding_model,
    metadatas=metadatas,
    persist_directory="./chroma_db_weight",
    collection_metadata={"hnsw:space": "cosine"} # 使用余弦相似度
)

def weighted_retriever(query, k=2, user_has_internal_access=True):
    """
    根据元数据分配权重，优先召回“高权重”文本块。
    """
    # 1. 基础向量检索：先取 k 的 3 倍作为候选池
    docs_with_scores = vector_db.similarity_search_with_score(query, k=k*3)
    
    weighted_docs = []
    current_time = datetime.now()
    
    for doc, distance in docs_with_scores:
        metadata = doc.metadata
        weight = 1.0

        # === 权重规则 1：时间新鲜度 (recency) ===
        update_str = metadata.get("recency", "")
        if update_str:
            try:
                update_date = datetime.strptime(update_str, "%Y-%m-%d")
                delta = current_time - update_date
                
                # 近 3 个月（约 90 天）
                if delta.days <= 90:
                    weight *= 1.2
                # 超过 1 年（约 365 天）
                elif delta.days > 365:
                    weight *= 0.8
            except ValueError:
                pass

        # === 权重规则 2：权限等级 (authorization) ===
        # 仅当检索者拥有内部权限时，对内部文档进行加权
        if metadata.get("authorization") == "internal" and user_has_internal_access:
            weight *= 1.1

        # 综合得分计算：
        # 1. 将距离(distance)转为相似度分 (0~1): 1 / (1 + distance)
        # 2. 乘以 metadata 权重
        base_score = 1.0 / (1.0 + distance)
        final_score = base_score * weight
        
        weighted_docs.append((doc, final_score, metadata))

    # 2. 按最终综合得分降序排序
    weighted_docs.sort(key=lambda x: x[1], reverse=True)
    
    return weighted_docs[:k]

# 步骤4：测试检索
query = "Java岗位的要求是什么？"
print(f"🔍 查询问题: {query}")
# 模拟当前用户拥有内部权限
results = weighted_retriever(query, k=2, user_has_internal_access=True)

print("\n🏆 元数据加权召回结果（优先展示：近期更新 & 内部可见）：")
for i, (doc, score, meta) in enumerate(results):
    print(f"🥇 排名 {i+1}: 综合得分 {score:.4f}")
    print(f"   📝 内容: {doc.page_content}")
    print(f"   🏷️ 更新时间: {meta['recency']}, 权限: {meta['authorization']}\n")