from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from app import llm
from app.chunking import chunk_text


class DocumentInput(BaseModel):
    id: str
    text: str

    @field_validator("id", "text")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or whitespace only")
        return value


class IngestRequest(BaseModel):
    documents: list[DocumentInput] = Field(min_length=1)


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty or whitespace only")
        return value


@dataclass
class Chunk:
    chunk_id: str
    text: str
    vector: list[float]


def create_app() -> FastAPI:
    """Return a new app with an empty, per-instance in-memory store."""
    app = FastAPI()
    store: dict[str, list[Chunk]] = {}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/ingest")
    def ingest(request: IngestRequest):
        total_chunks = 0
        for document in request.documents:
            chunks = [
                Chunk(
                    chunk_id=f"{document.id}:{index}",
                    text=text,
                    vector=llm.embed(text),
                )
                for index, text in enumerate(chunk_text(document.text))
            ]
            store[document.id] = chunks
            total_chunks += len(chunks)
        return {"ingested": len(request.documents), "chunks": total_chunks}

    @app.post("/ask")
    def ask(request: AskRequest):
        all_chunks = [chunk for chunks in store.values() for chunk in chunks]
        if not all_chunks:
            raise HTTPException(status_code=404, detail="No documents ingested")

        question_vector = llm.embed(request.question)
        scored = sorted(
            (
                (sum(a * b for a, b in zip(question_vector, chunk.vector)), doc_id, chunk)
                for doc_id, chunks in store.items()
                for chunk in chunks
            ),
            key=lambda item: item[0],
            reverse=True,
        )[: request.top_k]
        contexts = [chunk.text for _, _, chunk in scored]
        return {
            "answer": llm.generate(request.question, contexts),
            "sources": [
                {
                    "doc_id": doc_id,
                    "chunk_id": chunk.chunk_id,
                    "score": score,
                    "text": chunk.text,
                }
                for score, doc_id, chunk in scored
            ],
        }

    @app.get("/documents")
    def documents():
        return {
            "documents": [
                {"id": doc_id, "chunks": len(chunks)}
                for doc_id, chunks in sorted(store.items())
            ]
        }

    @app.delete("/documents/{doc_id}", status_code=204)
    def delete_document(doc_id: str) -> Response:
        if doc_id not in store:
            raise HTTPException(status_code=404, detail="Document not found")
        del store[doc_id]
        return Response(status_code=204)

    return app


app = create_app()
