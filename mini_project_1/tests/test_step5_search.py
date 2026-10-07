import numpy as np
import pytest
from langchain_core.documents import Document

from mini_project_1.src.step5_search import build_vector_store, cosine_similarity, search


def chunk(chunk_id: str, text: str, doc_type: str = "policy") -> Document:
    return Document(page_content=text, metadata={"chunk_id": chunk_id, "doc_id": chunk_id[:7], "doc_type": doc_type})


CHUNKS = [
    chunk("POL-001#000", "Rabaty powyżej 12% zatwierdza dyrektor handlowy."),
    chunk("POL-002#000", "Nowi klienci płacą w ciągu 14 dni."),
    chunk("REP-301#000", "OTIF do klientów spadł w Q2 do 94,1%.", doc_type="report"),
    chunk("MTG-402#000", "Od września ceny wody rosną o 4%.", doc_type="meeting_notes"),
]


@pytest.fixture
def store(fake_embeddings):
    return build_vector_store(CHUNKS, fake_embeddings)


def test_store_uses_chunk_ids(store):
    ids = [c.metadata["chunk_id"] for c in CHUNKS]
    found = sorted(d.id for d in store.get_by_ids(ids))
    assert found == sorted(ids), "identyfikatorem każdego chunku w bazie wektorowej musi być jego metadata['chunk_id']"


def test_search_returns_k_pairs_best_first(store):
    results = search(store, "Nowi klienci płacą w ciągu 14 dni.", k=3)
    assert len(results) == 3, f"oczekiwano k=3 wyników, otrzymano {len(results)}"
    top_chunk, top_score = results[0]
    assert top_chunk.metadata["chunk_id"] == "POL-002#000", "chunk o tym samym tekście musi być pierwszy"
    assert top_score == pytest.approx(1.0)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True), f"wyniki muszą być posortowane od najlepszego; wyniki podobieństwa: {scores}"


def test_search_filters_by_doc_type(store):
    results = search(store, "OTIF do klientów spadł w Q2 do 94,1%.", k=3, doc_type="policy")
    types = [c.metadata["doc_type"] for c, _ in results]
    assert types == ["policy", "policy"], f"z doc_type='policy' mogą wrócić tylko chunki typu policy; otrzymano {types}"


@pytest.mark.parametrize(
    "a, b, expected",
    [([1, 0], [1, 0], 1.0), ([1, 0], [0, 1], 0.0), ([1, 0], [-1, 0], -1.0), ([1, 0], [1, 1], 1 / np.sqrt(2)),
     ([3, 4], [6, 8], 1.0)],
)
def test_cosine_similarity(a, b, expected):
    got = cosine_similarity(a, b)
    assert isinstance(got, float), "cosine_similarity musi zwracać float Pythona"
    assert got == pytest.approx(expected), f"cosine_similarity({a}, {b}) powinno zwrócić {expected:.4f}, otrzymano {got}"


def test_cosine_similarity_zero_vector_raises():
    with pytest.raises(ValueError):
        cosine_similarity([0, 0], [1, 1])


def test_store_score_is_your_cosine_similarity(store, fake_embeddings):
    question = "Kto zatwierdza rabat 15%?"
    top_chunk, score = search(store, question, k=1)[0]
    mine = cosine_similarity(fake_embeddings.embed_query(question), fake_embeddings.embed_query(top_chunk.page_content))
    assert score == pytest.approx(mine), f"wynik z vector store {score:.4f} powinien być równy obliczonemu podobieństwu kosinusowemu {mine:.4f}"
