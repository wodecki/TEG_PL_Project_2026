"""Sprawdza gotowy układ promptu (helpers/prompts.py). Tu nic nie piszesz."""

from langchain_core.documents import Document

from helpers.prompts import build_prompt


def test_every_context_block_names_its_document():
    context = [Document(page_content="Zasada pierwsza.", metadata={"doc_id": "TST-001"}),
               Document(page_content="Zasada druga.", metadata={"doc_id": "TST-002"})]
    prompt = build_prompt("Przy każdym fakcie podaj identyfikator dokumentu.", context, "Które zasady obowiązują?")
    assert "[TST-001]\nZasada pierwsza." in prompt and "[TST-002]\nZasada druga." in prompt, \
        "model może się odwołać tylko do identyfikatorów dokumentów, które są w prompcie"
    assert prompt.endswith("Które zasady obowiązują?")
