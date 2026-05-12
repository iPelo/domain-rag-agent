class Reranker:
    def rerank(self, query: str, chunk_ids: list[str]) -> list[str]:
        raise NotImplementedError("Add a cross-encoder reranker after the baseline retriever works.")
