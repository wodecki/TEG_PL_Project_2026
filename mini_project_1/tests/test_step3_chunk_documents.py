import re

import pytest
from langchain_core.documents import Document

from helpers.embedding_cache import missing_from_cache
from mini_project_1.src.step3_chunk_documents import chunk_documents


@pytest.fixture(scope="module")
def chunks(documents, config):
    return chunk_documents(documents, config)


def test_returns_documents_no_longer_than_chunk_size(chunks, config):
    size = config.get("chunking.chunk_size")
    assert all(isinstance(c, Document) for c in chunks), "chunk_documents musi zwracać obiekty Document z LangChain"
    too_long = [c.metadata.get("chunk_id") for c in chunks if len(c.page_content) > size]
    assert not too_long, f"chunki dłuższe niż {size} znaków: {too_long[:3]}"


def test_every_document_is_chunked_in_order(chunks, documents):
    doc_order = [d.metadata["doc_id"] for d in documents]
    chunk_order = list(dict.fromkeys(c.metadata["doc_id"] for c in chunks))
    assert chunk_order == doc_order, "każdy dokument musi dać chunki, w kolejności dokumentów"


def test_chunks_keep_their_document_metadata(chunks, documents):
    first_doc = documents[0]
    first_chunk = chunks[0]
    missing = {k: v for k, v in first_doc.metadata.items() if first_chunk.metadata.get(k) != v}
    assert not missing, f"chunki muszą zachować metadane swojego dokumentu; brakujące lub zmienione: {missing}"


def test_chunk_ids_and_indexes(chunks):
    for chunk in chunks:
        doc_id, index, chunk_id = chunk.metadata["doc_id"], chunk.metadata.get("chunk_index"), chunk.metadata.get("chunk_id")
        expected = f"{doc_id}#{index:03d}" if isinstance(index, int) else "<doc_id>#<numer z 3 cyfr>"
        assert chunk_id == expected, f"chunk_id powinno być {expected!r}, otrzymano {chunk_id!r}"
    per_doc: dict[str, list[int]] = {}
    for chunk in chunks:
        per_doc.setdefault(chunk.metadata["doc_id"], []).append(chunk.metadata["chunk_index"])
    for doc_id, indexes in per_doc.items():
        assert indexes == list(range(len(indexes))), f"{doc_id}: chunk_index musi liczyć 0, 1, 2, ...; otrzymano {indexes}"
    assert re.fullmatch(r"[A-Z]+-\d{3}#\d{3}", chunks[0].metadata["chunk_id"])


def test_chunks_match_the_course_cache(chunks, config):
    """Cache kursu zawiera wektor każdego chunku zgodnego z ustawieniami kursu. Brak w cache oznacza, że twoje chunki
    różnią się od ustalonych co najmniej jednym znakiem: sprawdź trzy ustawienia splittera i nie
    zmieniaj tekstu chunków."""
    missing = missing_from_cache(config, [c.page_content for c in chunks])
    ids = [chunks[i].metadata["chunk_id"] for i in missing]
    assert not ids, f"{len(ids)} z {len(chunks)} chunków różni się od ustalonego podziału, np. {ids[:3]}"


def test_overlap_repeats_text_between_neighbours(config):
    text = " ".join(f"word{i}" for i in range(600))  # jeden długi akapit: wymusza podział w jego środku
    doc = Document(page_content=text, metadata={"doc_id": "TST-001"})
    pieces = chunk_documents([doc], config)
    assert len(pieces) > 1
    for left, right in zip(pieces, pieces[1:]):
        assert right.page_content.split()[0] in left.page_content.split(), \
            "sąsiednie chunki muszą na siebie zachodzić (użyj chunk_overlap z konfiguracji)"
