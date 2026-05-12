from qdrant_client import QdrantClient


class DenseRetriever:
    def __init__(self, qdrant_url: str, collection_name: str) -> None:
        self._client = QdrantClient(url=qdrant_url)
        self._collection_name = collection_name

    @property
    def collection_name(self) -> str:
        return self._collection_name
