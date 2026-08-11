import os
import re
from langchain.agents import create_agent
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.tools import tool

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME")

local_model_path = "../bge-small-zh-v1.5"


def extract_query_terms(query):
    """提取问题中需要同时出现在文档里的核心查询项。"""
    text = re.sub(r"[？?！!。]", "", query).strip()
    for ending in ("分别是多少", "是多少", "是什么", "有哪些", "有多少"):
        if text.endswith(ending):
            text = text[:-len(ending)]
            break

    focus = text.rsplit("的", 1)[-1]
    terms = re.split(r"[和与及、,，；;:\s]+", focus)
    return list(dict.fromkeys(term for term in terms if len(term) >= 2 and not term.isdigit()))


def retrieve_relevant_docs(vectorstore, query, k=3):
    """组合全文关键词检索和向量检索，提升精确事实问题的召回率。"""
    terms = extract_query_terms(query)
    keyword_docs = []

    if len(terms) >= 2:
        where_document = {
            "$and": [{"$contains": term} for term in terms]
        }
        matches = vectorstore.get(
            where_document=where_document,
            include=["documents", "metadatas"],
        )
        keyword_docs = [
            Document(page_content=content, metadata=metadata or {})
            for content, metadata in zip(matches["documents"], matches["metadatas"])
            if content
        ]

    semantic_docs = vectorstore.similarity_search(query, k=max(k * 4, 12))
    merged_docs = keyword_docs + semantic_docs
    unique_docs = []
    seen = set()
    for doc in merged_docs:
        identity = (doc.metadata.get("source"), doc.metadata.get("page"), doc.page_content)
        if identity not in seen:
            seen.add(identity)
            unique_docs.append(doc)

    return unique_docs[:k]


def run_rag_agent(persist_directory="./chroma_db"):
    if not os.path.exists(persist_directory):
        print(f"❌ 找不到向量数据库目录 '{persist_directory}'，请先运行 2_vector_builder.py。")
        return

    print("▶ 正在加载嵌入模型...")
    embeddings = HuggingFaceEmbeddings(
        model_name=local_model_path,
        model_kwargs={"device": "cuda"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print("▶ 正在加载本地向量数据库...")
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key, base_url=base_url)

    @tool
    def search_annual_report(query: str) -> str:
        """检索华为投资控股有限公司2025年年度报告，返回回答问题所需的原文片段。"""
        docs = retrieve_relevant_docs(vectorstore, query)
        if not docs:
            return "检索不到相关文档内容。"

        print(f"\n📄 检索到的分块数量：{len(docs)}")
        context_parts = []
        for index, doc in enumerate(docs, start=1):
            page = doc.metadata.get("page")
            page_label = f"第 {page + 1} 页" if isinstance(page, int) else "页码未知"
            print(f"--- 分块 {index}（{page_label}）---")
            print(doc.page_content)
            context_parts.append(f"【分块 {index}，{page_label}】\n{doc.page_content}")
        return "\n\n".join(context_parts)

    agent = create_agent(
        model=llm,
        tools=[search_annual_report],
        system_prompt=(
            "你是华为投资控股有限公司2025年年度报告分析助手。"
            "这是一个多轮对话，请结合历史消息理解用户的省略、指代和追问。"
            "回答涉及年报事实的问题前，必须调用 search_annual_report 工具检索原文；"
            "如果用户的问题依赖上一轮内容，也要把必要的上下文整理后传给工具。"
            "只能依据工具返回的年报内容回答，不得凭空编造。"
            "如果文档中找不到答案，请直接说“根据提供的文档，我无法回答该问题”。"
            "回答时使用中文，并尽量给出数据对应的年份和单位。"
        ),
    )

    print("华为年度报告多轮问答 Agent 已启动，输入 exit 退出。")
    messages = []
    while True:
        question = input("用户：").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit", "退出"}:
            break

        messages.append(("user", question))
        print("🤖 正在处理，请稍候...\n")
        result = agent.invoke({"messages": messages})
        messages = result["messages"]
        print(f"助手：{messages[-1].content}\n")

if __name__ == "__main__":
    run_rag_agent()
