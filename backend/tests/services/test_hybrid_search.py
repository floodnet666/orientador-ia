import pytest
from app.services.hybrid_search import _set_union_merge


def _doc(doc_id: str, score: float, text: str) -> dict:
    """Factory helper para reduzir boilerplate nos testes."""
    return {"id": doc_id, "score": score, "payload": {"text": text}}


class TestSetUnionMerge:
    """
    Suite TDD para _set_union_merge (SUM).
    R(q) = D(q) ⊕ (S(q) \\ D(q))
    """

    def test_preserves_dense_order_and_appends_sparse_anchors(self):
        """
        Caso canónico da spec: ordem densa preservada, âncoras léxicas
        posicionadas conforme o score (spec §5.3).

        doc_3 tem score 22.1 > sparse_interjection_threshold (20.0), portanto
        é injectado na posição 1 (logo após o melhor resultado denso).
        """
        dense = [
            _doc("doc_1", 0.9, "Contexto geral sobre Bourdieu"),
            _doc("doc_2", 0.8, "Mais teoria sociológica"),
        ]
        sparse = [
            _doc("doc_2", 15.4, "Mais teoria sociológica"),   # já no denso
            _doc("doc_3", 22.1, "Bourdieu 1979, página 45"),  # score > 20.0 → posição 1
        ]

        merged = _set_union_merge(dense, sparse, limit=5)

        # doc_3 score=22.1 > threshold=20.0 → intercalado na posição 1
        assert len(merged) == 3
        assert merged[0]["id"] == "doc_1"  # melhor resultado denso
        assert merged[1]["id"] == "doc_3"  # âncora de alto score intercalada
        assert merged[2]["id"] == "doc_2"  # segundo resultado denso (deslocado)
        assert merged[1]["payload"]["is_anchor"] is True
        assert merged[2]["payload"]["is_anchor"] is False

    def test_no_duplication_when_sparse_subset_of_dense(self):
        """Se todos os esparsos já estiverem no denso, retorna apenas o denso."""
        dense = [_doc("a", 0.9, "texto a"), _doc("b", 0.8, "texto b")]
        sparse = [_doc("a", 5.0, "texto a"), _doc("b", 4.0, "texto b")]

        merged = _set_union_merge(dense, sparse, limit=10)

        assert len(merged) == 2
        ids = {d["id"] for d in merged}
        assert ids == {"a", "b"}

    def test_limit_is_respected(self):
        """O resultado nunca excede o limite B."""
        dense = [_doc(f"d{i}", 1.0 - i * 0.1, f"texto denso {i}") for i in range(4)]
        sparse = [_doc(f"s{i}", float(i * 5), f"texto esparso {i}") for i in range(4)]

        merged = _set_union_merge(dense, sparse, limit=5)

        assert len(merged) <= 5

    def test_high_score_anchor_interjected_at_position_1(self):
        """
        Âncora com score > sparse_interjection_threshold deve ser injectada
        na posição 1 (logo após o melhor resultado denso).
        """
        dense = [
            _doc("d1", 0.9, "texto denso principal"),
            _doc("d2", 0.8, "texto denso secundário"),
        ]
        sparse = [_doc("s1", 99.0, "referência exacta página 12")]  # score muito alto

        merged = _set_union_merge(dense, sparse, limit=5, sparse_interjection_threshold=20.0)

        assert merged[1]["id"] == "s1"
        assert merged[1]["payload"]["is_anchor"] is True

    def test_low_score_anchor_appended_at_end(self):
        """Âncora com score baixo deve ser adicionada ao final."""
        dense = [_doc("d1", 0.9, "texto denso")]
        sparse = [_doc("s1", 5.0, "âncora fraca")]  # score abaixo do threshold

        merged = _set_union_merge(dense, sparse, limit=10, sparse_interjection_threshold=20.0)

        assert merged[-1]["id"] == "s1"

    def test_original_payload_not_mutated(self):
        """A função não deve mutar os dicts de entrada originais."""
        dense = [_doc("d1", 0.9, "texto")]
        original_payload = dense[0]["payload"].copy()

        _set_union_merge(dense, [], limit=5)

        assert dense[0]["payload"] == original_payload  # sem is_anchor injectado no original

    def test_empty_dense_returns_sparse_as_anchors(self):
        """Com dense vazio, todos os esparsos são âncoras."""
        sparse = [_doc("s1", 10.0, "âncora"), _doc("s2", 5.0, "âncora 2")]

        merged = _set_union_merge([], sparse, limit=5)

        assert all(d["payload"]["is_anchor"] is True for d in merged)
        assert len(merged) == 2
