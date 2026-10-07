import pytest
from langchain_core.documents import Document

from mini_project_1.src.step1_load_documents import load_documents


def test_returns_one_document_per_markdown_file(documents, config):
    n_files = len(list(config.path("paths.corpus_dir").glob("*.md")))
    assert isinstance(documents, list) and all(isinstance(d, Document) for d in documents), \
        "load_documents musi zwracać listę obiektów Document z LangChain"
    assert len(documents) == n_files, f"oczekiwano {n_files} dokumentów (po jednym na plik .md), otrzymano {len(documents)}"


def test_sorted_by_doc_id(documents):
    ids = [d.metadata.get("doc_id") for d in documents]
    assert ids == sorted(ids), f"dokumenty muszą być posortowane według doc_id; otrzymano {ids[:4]} ..."


def test_metadata_is_the_catalog_row_plus_source(documents, config):
    expected_keys = {*config.get("corpus.required_metadata"), "source"}
    first = documents[0]
    assert set(first.metadata) == expected_keys, (
        f"klucze metadata muszą być dokładnie takie: {sorted(expected_keys)}; otrzymano {sorted(first.metadata)}"
    )
    assert first.metadata["doc_id"] == "CON-101" and first.metadata["doc_type"] == "contract"
    assert first.metadata["source"] == "CON-101_supplier_agreement_mleczna_dolina.md", \
        f"'source' musi być samą nazwą pliku, otrzymano {first.metadata['source']!r}"


def test_page_content_is_the_file_text_unchanged(documents, config):
    for doc in documents:
        text = (config.path("paths.corpus_dir") / doc.metadata["source"]).read_text(encoding="utf-8")
        assert doc.page_content == text, (
            f"{doc.metadata['source']}: page_content musi być tekstem pliku bez żadnych zmian. "
            "Jeśli polskie litery wyglądają źle (np. 'WĂłzki' zamiast 'Wózki'), czytaj pliki jako UTF-8."
        )


def test_polish_document_is_loaded(documents):
    assert {d.metadata["language"] for d in documents} == {"en", "pl"}


def test_works_on_another_corpus(toy_corpus):
    add, config = toy_corpus
    add("b.md", "Drugi.", doc_id="BBB-001")
    add("a.md", "Pierwszy.", doc_id="AAA-001", doc_type="report")
    docs = load_documents(config)
    assert [d.page_content for d in docs] == ["Pierwszy.", "Drugi."]
    assert docs[0].metadata["doc_type"] == "report"


def test_catalog_csv_is_not_a_document(toy_corpus):
    add, config = toy_corpus
    add("a.md")
    assert len(load_documents(config)) == 1, "dokumentami są tylko pliki .md, a nie catalog.csv"


def test_file_without_catalog_row_raises(toy_corpus):
    add, config = toy_corpus
    add("listed.md")
    add("stray.md", in_catalog=False)
    with pytest.raises(ValueError, match="stray.md"):
        load_documents(config)


def test_empty_catalog_field_raises(toy_corpus):
    add, config = toy_corpus
    add("no_owner.md", owner="")
    with pytest.raises(ValueError, match="no_owner.md"):
        load_documents(config)
