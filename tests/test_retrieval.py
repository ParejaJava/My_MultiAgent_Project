from app.rag.retriever import retrieve_documents


def test_retrieve_documents_returns_source_information() -> None:
    results = retrieve_documents("timeout")

    assert results
    assert results[0].startswith("data/docs/")
