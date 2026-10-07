import re

import pytest
from langchain_core.documents import Document

from helpers.embedding_cache import missing_from_cache
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks


@pytest.fixture(scope="module")
def chunks(config):
    from mini_project_1.src.step1_load_documents import load_documents

    return build_contextual_chunks(load_documents(config), config)


def test_toy_document_gets_title_and_section_headers(config):
    doc = Document(page_content="# Zasady floty\n\nDotyczą wszystkich furgonetek.\n\n## Kierowcy\n\nTylko kierowcy z prawem jazdy.",
                   metadata={"doc_id": "TST-001", "title": "Zasady floty", "language": "pl"})
    out = build_contextual_chunks([doc], config)
    assert [c.page_content.split("\n\n")[0] for c in out] == ["Zasady floty", "Zasady floty > Kierowcy"], \
        "każdy chunk musi zaczynać się od '<title> > <section>' (sam '<title>', gdy nie ma nagłówka ##)"
    assert [c.metadata["section"] for c in out] == ["", "Kierowcy"]
    assert [c.metadata["chunk_id"] for c in out] == ["TST-001#ctx000", "TST-001#ctx001"]
    assert out[1].metadata["language"] == "pl", "zachowaj wszystkie pola metadata dokumentu"
    assert "## Kierowcy" in out[1].page_content, "zostaw nagłówki w tekście"


def test_chunk_ids_are_numbered_per_document(chunks):
    assert all(re.fullmatch(r"[A-Z]+-\d{3}#ctx\d{3}", c.metadata["chunk_id"]) for c in chunks)
    firsts = {c.metadata["doc_id"] for c in chunks if c.metadata["chunk_id"].endswith("#ctx000")}
    assert firsts == {c.metadata["doc_id"] for c in chunks}, "numeracja zaczyna się od ctx000 w każdym dokumencie"
    assert len({c.metadata["chunk_id"] for c in chunks}) == len(chunks), "id chunków muszą być unikalne"


def test_every_chunk_starts_with_its_document_title(chunks):
    bad = [c.metadata["chunk_id"] for c in chunks if not c.page_content.startswith(c.metadata["title"])]
    assert not bad, f"chunki, które nie zaczynają się od tytułu swojego dokumentu: {bad[:3]}"


def test_chunks_match_the_course_cache(chunks, config):
    """Pamięć podręczna kursu zawiera wektory wszystkich chunków z kontekstem, utworzonych zgodnie z ustawieniami kursu."""
    missing = missing_from_cache(config, [c.page_content for c in chunks])
    ids = [chunks[i].metadata["chunk_id"] for i in missing]
    assert not ids, (f"chunki inne niż oczekiwane: {len(ids)} z {len(chunks)}, np. {ids[:3]}. "
                     "Sprawdź splittery, ustawienia podziału z konfiguracji i format nagłówka")
