from uuid import uuid4

from app.rag.bm25 import BM25Document, BM25Index, tokenize
from app.rag.retriever import reciprocal_rank_fusion


def test_chinese_bigram_and_ascii_tokenization() -> None:
    assert tokenize("拖欠工资 API-v2") == [
        "a:api",
        "a:v2",
        "c:拖欠",
        "c:欠工",
        "c:工资",
    ]
    assert tokenize("税") == ["c:税"]


def test_bm25_prefers_matching_document_and_has_stable_ties() -> None:
    index = BM25Index(
        [
            BM25Document("b", "房屋租赁押金返还"),
            BM25Document("a", "用人单位拖欠工资"),
            BM25Document("c", "车辆发生追尾事故"),
        ]
    )

    results = index.search("公司一直拖欠工资", limit=2)

    assert results[0][0] == "a"
    assert all(score > 0 for _, score in results)


def test_rrf_merges_deduplicates_and_supports_one_empty_route() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()

    fused = reciprocal_rank_fusion([first, second], [second, third])
    vector_only = reciprocal_rank_fusion([first, second], [])

    assert [item[0] for item in fused] == [second, first, third]
    assert fused[0][2:] == (2, 1)
    assert [item[0] for item in vector_only] == [first, second]
    assert vector_only[0][3] is None
