import os
import re
from collections import Counter
from collections.abc import Callable, Sequence
from math import log
from pathlib import Path

import torch
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from transformers import AutoModelForSequenceClassification, AutoTokenizer


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ===================== 配置 =====================
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_NAME")

# 标准 RRF 默认等权，避免单路候选在进入精排前被整体压制。
DENSE_WEIGHT = 1.0
SPARSE_WEIGHT = 1.0
RETRIEVAL_TOP_K = 12
RRF_K = 60
RRF_TOP_K = 8
RERANK_TOP_K = 3

local_embed_path = BASE_DIR / "bge-small-zh-v1.5"
local_rerank_path = BASE_DIR / "bge-reranker-base"


# ===================== 本地 Reranker =====================
class LocalReranker:
    """使用 BGE Cross-Encoder 对候选文档进行精排。"""

    def __init__(self, model_path: str | Path, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
        self.model.to(self.device)
        self.model.eval()

    def rank(
        self,
        query: str,
        docs: Sequence[Document],
        batch_size: int = 8,
    ) -> list[tuple[Document, float]]:
        """返回按相关性分数从高到低排列的 ``(文档, 分数)``。"""
        if not docs:
            return []

        scores: list[float] = []
        with torch.inference_mode():
            for start in range(0, len(docs), batch_size):
                batch_docs = docs[start : start + batch_size]
                inputs = self.tokenizer(
                    [query] * len(batch_docs),
                    [doc.page_content for doc in batch_docs],
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=512,
                )
                inputs = {name: tensor.to(self.device) for name, tensor in inputs.items()}
                logits = self.model(**inputs, return_dict=True).logits.view(-1)
                scores.extend(logits.float().cpu().tolist())

        return sorted(zip(docs, scores), key=lambda item: item[1], reverse=True)


# ===================== 检索工具函数 =====================
def tokenize_for_bm25(text: str) -> list[str]:
    """为中英文混合文本生成 BM25 词元，无需额外中文分词依赖。"""
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", normalized)
    chinese_segments = re.findall(r"[\u4e00-\u9fff]+", normalized)

    chinese_tokens: list[str] = []
    for segment in chinese_segments:
        chinese_tokens.extend(segment)
        chinese_tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))

    return latin_tokens + chinese_tokens


class SparseBM25Retriever:
    """轻量 BM25 稀疏检索器，接口与 LangChain Retriever 的用法一致。"""

    def __init__(
        self,
        docs: Sequence[Document],
        preprocess_func: Callable[[str], list[str]] = tokenize_for_bm25,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.docs = list(docs)
        self.preprocess_func = preprocess_func
        self.k1 = k1
        self.b = b
        self.k = 4

        tokenized_docs = [preprocess_func(doc.page_content) for doc in self.docs]
        self.term_frequencies = [Counter(tokens) for tokens in tokenized_docs]
        self.doc_lengths = [len(tokens) for tokens in tokenized_docs]
        self.avg_doc_length = (
            sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        )

        document_frequencies: Counter[str] = Counter()
        for term_frequency in self.term_frequencies:
            document_frequencies.update(term_frequency.keys())
        doc_count = len(self.docs)
        self.idf = {
            term: log(1 + (doc_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    @classmethod
    def from_documents(
        cls,
        docs: Sequence[Document],
        preprocess_func: Callable[[str], list[str]] = tokenize_for_bm25,
    ) -> "SparseBM25Retriever":
        return cls(docs, preprocess_func=preprocess_func)

    def invoke(self, query: str) -> list[Document]:
        query_terms = Counter(self.preprocess_func(query))
        scored_docs: list[tuple[float, int, Document]] = []

        for index, (doc, term_frequency, doc_length) in enumerate(
            zip(self.docs, self.term_frequencies, self.doc_lengths)
        ):
            score = 0.0
            length_normalization = (
                doc_length / self.avg_doc_length if self.avg_doc_length else 0.0
            )
            for term, query_frequency in query_terms.items():
                frequency = term_frequency.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length_normalization
                )
                score += (
                    self.idf.get(term, 0.0)
                    * (frequency * (self.k1 + 1) / denominator)
                    * query_frequency
                )
            scored_docs.append((score, index, doc))

        scored_docs.sort(key=lambda item: (-item[0], item[1]))
        return [doc for _, _, doc in scored_docs[: self.k]]


def get_all_docs(vectorstore: Chroma) -> list[Document]:
    data = vectorstore.get(include=["documents", "metadatas"])
    return [
        Document(page_content=content, metadata=metadata or {})
        for content, metadata in zip(data["documents"], data["metadatas"])
        if content
    ]


def document_key(doc: Document) -> tuple[str, object, str]:
    """用来源、页码和内容共同标识文档，避免不同页面的重复文本被误合并。"""
    return (
        str(doc.metadata.get("source", "")),
        doc.metadata.get("page"),
        doc.page_content,
    )


def reciprocal_rank_fusion(
    rankings: Sequence[tuple[Sequence[Document], float, str]],
    rrf_k: int = RRF_K,
    top_k: int = RRF_TOP_K,
) -> list[Document]:
    """按加权 RRF 融合多个有序结果列表，并把排名信息写入文档元数据。"""
    if rrf_k < 0:
        raise ValueError("rrf_k 必须大于或等于 0")
    if top_k <= 0:
        return []

    scores: dict[tuple[str, object, str], float] = {}
    docs_by_key: dict[tuple[str, object, str], Document] = {}
    ranks_by_key: dict[tuple[str, object, str], dict[str, int]] = {}

    for docs, weight, retrieval_name in rankings:
        seen_in_ranking: set[tuple[str, object, str]] = set()
        for rank, doc in enumerate(docs, start=1):
            key = document_key(doc)
            if key in seen_in_ranking:
                continue
            seen_in_ranking.add(key)
            docs_by_key.setdefault(key, doc)
            scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank)
            ranks_by_key.setdefault(key, {})[retrieval_name] = rank

    ordered_keys = sorted(
        scores,
        key=lambda key: (-scores[key], key[0], str(key[1]), key[2]),
    )
    fused_docs: list[Document] = []
    for key in ordered_keys[:top_k]:
        doc = docs_by_key[key]
        metadata = dict(doc.metadata)
        metadata["rrf_score"] = scores[key]
        metadata["retrieval_ranks"] = ranks_by_key[key]
        fused_docs.append(Document(page_content=doc.page_content, metadata=metadata))
    return fused_docs


def hybrid_retrieve(
    query: str,
    vectorstore: Chroma,
    reranker: LocalReranker,
    retrieval_top_k: int = RETRIEVAL_TOP_K,
    rrf_top_k: int = RRF_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
    sparse_retriever_factory: Callable[[Sequence[Document]], SparseBM25Retriever] | None = None,
) -> list[Document]:
    """执行 BM25 + 稠密检索、RRF 融合以及 Cross-Encoder 精排。"""
    all_docs = get_all_docs(vectorstore)
    if not all_docs:
        return []

    if sparse_retriever_factory is None:
        sparse_retriever = SparseBM25Retriever.from_documents(
            all_docs,
            preprocess_func=tokenize_for_bm25,
        )
    else:
        sparse_retriever = sparse_retriever_factory(all_docs)
    sparse_retriever.k = min(retrieval_top_k, len(all_docs))
    sparse_docs = sparse_retriever.invoke(query)

    dense_docs = vectorstore.similarity_search(
        query,
        k=min(retrieval_top_k, len(all_docs)),
    )

    fused_docs = reciprocal_rank_fusion(
        [
            (dense_docs, DENSE_WEIGHT, "dense"),
            (sparse_docs, SPARSE_WEIGHT, "sparse"),
        ],
        top_k=rrf_top_k,
    )

    reranked = reranker.rank(query, fused_docs)
    final_docs: list[Document] = []
    for doc, rerank_score in reranked[:rerank_top_k]:
        metadata = dict(doc.metadata)
        metadata["rerank_score"] = rerank_score
        final_docs.append(Document(page_content=doc.page_content, metadata=metadata))
    return final_docs


def format_docs(docs: Sequence[Document]) -> str:
    context_parts = []
    for index, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page")
        page_label = f"第 {page + 1} 页" if isinstance(page, int) else "页码未知"
        context_parts.append(f"【参考片段 {index}，{page_label}】\n{doc.page_content}")
    return "\n\n".join(context_parts)


# ===================== RAG 主流程 =====================
def run_rag_qa(query: str, persist_directory: str | Path | None = None) -> str | None:
    persist_path = Path(persist_directory) if persist_directory else BASE_DIR / "chroma_db"
    if not persist_path.exists():
        print(f"❌ 找不到向量数据库目录：{persist_path}，请先运行 2_vector_builder.py。")
        return None

    print("▶ 正在加载嵌入模型和向量数据库...")
    embedding_device = "cuda" if torch.cuda.is_available() else "cpu"
    embeddings = HuggingFaceEmbeddings(
        model_name=str(local_embed_path),
        model_kwargs={"device": embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = Chroma(
        persist_directory=str(persist_path),
        embedding_function=embeddings,
    )

    print("▶ 正在执行稠密检索 + BM25 + RRF 融合 + Reranker 精排...")
    reranker = LocalReranker(local_rerank_path)
    final_docs = hybrid_retrieve(query, vectorstore, reranker)
    if not final_docs:
        print("未检索到可用文档。")
        return None

    print("\n" + "=" * 60)
    print(f"✅ 检索与精排完成，返回 {len(final_docs)} 条")
    print("=" * 60)
    for index, doc in enumerate(final_docs, start=1):
        ranks = doc.metadata.get("retrieval_ranks", {})
        dense_rank = ranks.get("dense", "-")
        sparse_rank = ranks.get("sparse", "-")
        print(
            f"\n结果 {index} | 稠密排名: {dense_rank} | BM25 排名: {sparse_rank} "
            f"| RRF: {doc.metadata['rrf_score']:.6f} "
            f"| Reranker: {doc.metadata['rerank_score']:.4f}"
        )
        print(doc.page_content)

    llm = ChatOpenAI(
        model=model_name,
        temperature=0,
        api_key=api_key,
        base_url=base_url,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是企业内部文档问答助手。\n"
                "请严格基于以下参考文档回答用户问题。\n"
                "如果找不到答案，请直接说“根据提供的文档，我无法回答该问题”，不要编造。\n\n"
                "【参考文档】\n{context}",
            ),
            ("human", "{input}"),
        ]
    )
    rag_chain = prompt | llm | StrOutputParser()

    print("\n================ 问答 ================")
    print(f"问题：{query}")
    answer = rag_chain.invoke({"context": format_docs(final_docs), "input": query})
    print(f"\n回答：\n{answer}")
    print("=" * 60)
    return answer


if __name__ == "__main__":
    run_rag_qa("节日和生日福利有什么？")
