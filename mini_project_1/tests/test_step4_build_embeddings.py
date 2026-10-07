from helpers.eval_queries import load_eval_queries
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.tests.conftest import ForbiddenEmbeddings, config_with


def test_texts_are_embedded_once_then_served_from_the_cache(tmp_path, config, fake_embeddings):
    embeddings = build_embeddings(config_with(config, embedding_cache=tmp_path), underlying=fake_embeddings)
    first = embeddings.embed_documents(["alpha", "beta"])
    second = embeddings.embed_documents(["alpha", "beta"])
    assert fake_embeddings.calls == ["alpha", "beta"], \
        "drugie wywołanie musi korzystać z cache, bez ponownego wywołania modelu"
    assert first == second


def test_questions_are_cached_too(tmp_path, config, fake_embeddings):
    embeddings = build_embeddings(config_with(config, embedding_cache=tmp_path), underlying=fake_embeddings)
    embeddings.embed_query("Kto zatwierdza rabat 15%?")
    embeddings.embed_query("Kto zatwierdza rabat 15%?")
    assert fake_embeddings.calls == ["Kto zatwierdza rabat 15%?"], \
        "pytania (embed_query) też muszą trafiać do cache"


def test_cache_is_stored_in_the_configured_folder(tmp_path, config, fake_embeddings):
    folder = tmp_path / "my_cache"
    build_embeddings(config_with(config, embedding_cache=folder), underlying=fake_embeddings).embed_documents(["alpha"])
    names = [p.name for p in folder.iterdir()] if folder.exists() else []
    assert names, "cache musi być zapisywany w config.path('paths.embedding_cache')"
    model = config.get("embeddings.model")
    assert all(n.startswith(model) and len(n) == len(model) + 64 for n in names), \
        f"pliki cache muszą się nazywać <nazwa modelu><sha256 tekstu>; otrzymano np. {names[0]!r}"


def test_the_course_cache_answers_every_test_question(config):
    embeddings = build_embeddings(config, underlying=ForbiddenEmbeddings())
    for query in load_eval_queries(config.path("paths.eval_queries")):
        vector = embeddings.embed_query(query.question)
        assert len(vector) == config.get("embeddings.dimensions")
