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
- Continuous code quality validation (`make check`)
- Linting and automatic formatting enforcement (Ruff)
- In-depth architectural and code validation (Pyrefly)
- Strict compliance with modern Python typing standards
- Maximum 88-character line length enforcement (E501)
- Bug-prevention and safety rule enforcement (flake8-bugbear)
- Systematic performance and syntax upgrades (pyupgrade)
- Interface consistency and abstract method validation (B024)
- Automated type-safety and modern typing usage (UP042)
- Docker-powered CI pipeline (GitHub Actions) for consistent validation across push and PRs (linting, migrations, and test suite).

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
- Hierarchical Summarization (RAPTOR) for high-level technical query retrieval via Python structural code unit analysis (classes, functions, modules) and summary nodes.
