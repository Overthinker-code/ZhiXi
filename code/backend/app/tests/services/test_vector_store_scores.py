from app.services.vector_store import VectorStore


def test_hash_distance_to_relevance_is_bounded() -> None:
    assert VectorStore._hash_distance_to_relevance(0.0) == 1.0
    assert VectorStore._hash_distance_to_relevance(1.0) == 0.5
    assert VectorStore._hash_distance_to_relevance(2.0) == 0.0
    assert VectorStore._hash_distance_to_relevance(4.0) == 0.0
