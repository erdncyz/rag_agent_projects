from __future__ import annotations
import re
from collections import Counter
from typing import Optional


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    # Türkçe karakter desteği ile temizleme
    text = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [token for token in normalized.split() if token]


def lexical_overlap_score(query: str, document: str) -> float:
    """Kelime bazlı çakışma (overlap) skoru üretir."""
    query_tokens = tokenize(query)
    doc_tokens = tokenize(document)

    if not query_tokens or not doc_tokens:
        return 0.0

    query_counter = Counter(query_tokens)
    doc_counter = Counter(doc_tokens)

    overlap = 0
    for token, q_count in query_counter.items():
        overlap += min(q_count, doc_counter.get(token, 0))

    return overlap / max(len(query_tokens), 1)


def distance_to_similarity(distance: Optional[float]) -> float:
    """Vektör mesafesini (distance) benzerlik skoruna (0-1) çevirir."""
    if distance is None:
        return 0.0
    # Mesafe düştükçe benzerlik artsın (1 -> tam eşleşme, 0 -> hiç eşleşmeme)
    return 1 / (1 + max(distance, 0))


def hybrid_score(
    vector_similarity: float,
    lexical_score: float,
    vector_weight: float,
    lexical_weight: float,
) -> float:
    """Vektör ve kelime bazlı skorları ağırlıklı olarak birleştirir."""
    return (vector_similarity * vector_weight) + (lexical_score * lexical_weight)


def rerank_score(
    question: str,
    document_text: str,
    vector_distance: Optional[float],
) -> float:
    """Rerank için hibrit bir skor hesaplar."""
    lexical = lexical_overlap_score(question, document_text)
    semantic = distance_to_similarity(vector_distance)
    # Rerank için kelime bazlı (lexical) ağırlığı biraz artırıyoruz
    # Bu sayede anahtar kelime eşleşmeleri daha yukarı çıkar.
    return (semantic * 0.55) + (lexical * 0.45)
