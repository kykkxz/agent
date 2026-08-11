import importlib.util
import math
import unittest
from pathlib import Path

from langchain_core.documents import Document


MODULE_PATH = Path(__file__).with_name("4_rag_advance.py")
SPEC = importlib.util.spec_from_file_location("rag_advance", MODULE_PATH)
rag_advance = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rag_advance)


def make_doc(content: str, page: int) -> Document:
    return Document(
        page_content=content,
        metadata={"source": "test.pdf", "page": page},
    )


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.k = 0

    def invoke(self, _query):
        return self.docs[: self.k]


class FakeVectorStore:
    def __init__(self, corpus, dense_docs):
        self.corpus = corpus
        self.dense_docs = dense_docs

    def get(self, include):
        assert include == ["documents", "metadatas"]
        return {
            "documents": [doc.page_content for doc in self.corpus],
            "metadatas": [doc.metadata for doc in self.corpus],
        }

    def similarity_search(self, _query, k):
        return self.dense_docs[:k]


class FakeReranker:
    def rank(self, _query, docs):
        return sorted(
            ((doc, float(doc.metadata["page"])) for doc in docs),
            key=lambda item: item[1],
            reverse=True,
        )


class RagAdvanceTests(unittest.TestCase):
    def test_rrf_combines_dense_and_sparse_ranks(self):
        first = make_doc("共同候选", 1)
        second = make_doc("仅稠密召回", 2)
        third = make_doc("仅稀疏召回", 3)

        fused = rag_advance.reciprocal_rank_fusion(
            [
                ([first, second], 0.6, "dense"),
                ([first, third], 0.4, "sparse"),
            ],
            rrf_k=60,
            top_k=3,
        )

        self.assertEqual([doc.page_content for doc in fused], ["共同候选", "仅稠密召回", "仅稀疏召回"])
        self.assertTrue(
            math.isclose(fused[0].metadata["rrf_score"], 1 / 61, rel_tol=1e-9)
        )
        self.assertEqual(
            fused[0].metadata["retrieval_ranks"],
            {"dense": 1, "sparse": 1},
        )

    def test_hybrid_retrieve_reranks_rrf_candidates(self):
        first = make_doc("稠密第一", 1)
        second = make_doc("双路召回", 2)
        third = make_doc("稀疏第一", 3)
        vectorstore = FakeVectorStore(
            corpus=[first, second, third],
            dense_docs=[first, second],
        )

        final_docs = rag_advance.hybrid_retrieve(
            "测试问题",
            vectorstore,
            FakeReranker(),
            retrieval_top_k=2,
            rrf_top_k=3,
            rerank_top_k=2,
            sparse_retriever_factory=lambda _docs: FakeRetriever([third, second]),
        )

        self.assertEqual([doc.page_content for doc in final_docs], ["稀疏第一", "双路召回"])
        self.assertEqual([doc.metadata["rerank_score"] for doc in final_docs], [3.0, 2.0])
        self.assertIn("rrf_score", final_docs[0].metadata)

    def test_bm25_tokenizer_supports_chinese_bigrams_and_english(self):
        tokens = rag_advance.tokenize_for_bm25("员工 birthday 福利")

        self.assertIn("员工", tokens)
        self.assertIn("birthday", tokens)
        self.assertIn("福利", tokens)

    def test_sparse_bm25_retriever_prefers_matching_document(self):
        matching = make_doc("公司为员工提供节日福利和生日福利", 1)
        unrelated = make_doc("差旅报销需要提交有效发票", 2)
        retriever = rag_advance.SparseBM25Retriever.from_documents(
            [unrelated, matching]
        )
        retriever.k = 1

        result = retriever.invoke("生日福利")

        self.assertEqual(result, [matching])


if __name__ == "__main__":
    unittest.main()
