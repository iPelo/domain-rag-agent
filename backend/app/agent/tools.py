from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    title: str
    text: str
    score: float


class RetrievalTool:
    name = "retrieve"
    description = "Search the German law corpus for source passages."

    def __call__(self, query: str) -> list[RetrievedChunk]:
        raise NotImplementedError("Wire this to the hybrid retriever after ingestion is implemented.")
