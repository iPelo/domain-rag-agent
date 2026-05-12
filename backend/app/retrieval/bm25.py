from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self._tokenized = [_tokenize(text) for text in texts]
        self._index = BM25Okapi(self._tokenized)

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[int, float]]:
        scores = self._index.get_scores(_tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        return [(index, float(score)) for index, score in ranked[:top_k]]


def _tokenize(text: str) -> list[str]:
    return text.lower().split()
