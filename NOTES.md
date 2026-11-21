# Notes

- I used a per-app in-memory dictionary, which keeps each `create_app()` instance isolated.
- Chunks and their vectors are created during ingestion, so questions only need retrieval scoring.
- Re-ingestion replaces a document atomically at the document level and avoids stale chunks.
- With more time, I would add persistence, concurrent-write protection, and structured logging.
- I used Codex as an AI coding assistant for implementation and test review.
