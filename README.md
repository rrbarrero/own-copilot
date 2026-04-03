# AI Code Knowledge Assistant

AI Code Knowledge Assistant solves the problem of asking useful, grounded questions about a codebase or technical document set without relying on the model's memory alone. Instead of answering from generic knowledge, it ingests files and repository snapshots, indexes them, and retrieves relevant evidence so responses can stay tied to the actual source material, including exact code identifiers, paths, and citations.

## Design And Architecture Best Practices

- Domain-Driven Design (DDD)
- Hexagonal Architecture
- Separation of concerns
- Dependency inversion
- Composition root
- Protocol-driven interfaces
- Application services
- Repository pattern
- Strategy pattern
- Idempotent operations
- Asynchronous job processing
- Explicit state transitions
- Database migrations
- Unit testing
- Integration testing
- End-to-end testing
- Typed configuration management
- Infrastructure isolation

## AI Code Knowledge Assistant Best Practices

- Grounded answers from indexed source material
- Retrieval-Augmented Generation (RAG)
- Hybrid search
- Vector retrieval
- Lexical retrieval
- Reciprocal Rank Fusion (RRF)
- Repository-scoped retrieval
- Document-scoped retrieval
- Citation-based responses
- Conversational memory with scope consistency
- Query rewriting for follow-up questions
- Deterministic repository tools
- File-level inspection
- Exact text and symbol search
- Repository snapshot synchronization
- Incremental reindexing by content hash
- Document chunking for LLM retrieval
- Format-aware document normalization
