"""Odtwarza każdy dialog wzorcowy w TWOIM grafie copilota z IDEALNYM zrozumieniem wiadomości.

Bez LLM-a: udawany model zwraca wzorcowe `understand` każdej tury. Ten test sprawdza więc
workflow, stan wniosku i politykę, a nie zrozumienie wiadomości, które mierzy na żywo
run_dialogues.py. Nic tu nie piszesz; test używa twoich kroków 1–5.
"""


from helpers.embedding_cache import underlying_embeddings
from helpers.workflow import CopilotDeps, Turn, run_turn, new_checkpointer
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_3.src.step4_copilot_graph import build_copilot_graph
from mini_project_3.src.step5_score_transcript import score_transcript
from mini_project_3.tests.conftest import ReplayLLM, gold_dialogues


def test_every_gold_dialogue_replays_perfectly(config, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # cache musi dostarczyć każdy embedding
    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    transcript, gold = [], []
    for dialogue in gold_dialogues():
        llm = ReplayLLM([Turn(**t["understand"]) for t in dialogue["turns"]])
        graph = build_copilot_graph(CopilotDeps(llm=llm, store=store, config=config), new_checkpointer())
        for t in dialogue["turns"]:
            scripted = iter(t["resume"])
            transcript.append(run_turn(graph, dialogue["id"], t["user"], lambda payload: next(scripted)))
            gold.append(t["expect"])
    score = score_transcript(transcript, gold)
    wrong = [(d["user"], d["wrong"]) for d in score["details"] if d["wrong"]]
    assert not wrong, f"przy idealnym zrozumieniu każdy etap musi zgadzać się ze wzorcem; błędne: {wrong}"
    assert score["errors"] == 0
