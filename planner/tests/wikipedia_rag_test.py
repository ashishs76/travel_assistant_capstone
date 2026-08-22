from planner.rag import destination_retriever

def test_retrieve_returns_fact_and_citation():
    results = destination_retriever.retrieve_destination_context("Kyoto")
    assert len(results) == 1
    assert results[0]["fact"]
    assert results[0]["source_url"].startswith("https://en.wikipedia.org/")


def test_retrieve_unknown_place_returns_empty():
    results = destination_retriever.retrieve_destination_context("ASascasdads332 Nowhere")
    assert results == []


def test_retrieve_handles_multiword_place():
    results = destination_retriever.retrieve_destination_context("New York City")
    assert len(results) == 1
    assert "New York" in results[0]["source_title"]