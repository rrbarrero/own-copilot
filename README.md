# AI Code Knowledge Assistant

AI Code Knowledge Assistant solves the problem of asking useful, grounded questions about a codebase or technical document set without relying on the model's memory alone. Instead of answering from generic knowledge, it ingests files and repository snapshots, indexes them, and retrieves relevant evidence so responses can stay tied to the actual source material, including exact code identifiers, paths, and citations.

## Branch Review Use Case

The assistant can review a repository branch against `main` using synchronized
repository snapshots instead of generic model memory.

How it works:

1. Synchronize `main`.
2. Synchronize the target branch.
3. Resolve the latest completed snapshots for both branches.
4. Compute the diff between `main` and the target branch.
5. Generate structured review findings with severity, file path, and line range.

Example:

```bash
uv run python scripts/api_client.py sync-repo https://github.com/rrbarrero/credit-fraud.git

uv run python scripts/api_client.py sync-repo \
  https://github.com/rrbarrero/credit-fraud.git \
  --branch new-model-llm-evaluation

uv run python scripts/api_client.py review-branch \
  e2196e4e-fc51-46ec-aeff-f56cc36e08cd \
  new-model-llm-evaluation
```

Example response:

```json
{
  "repository_id": "e2196e4e-fc51-46ec-aeff-f56cc36e08cd",
  "base_branch": "main",
  "branch": "new-model-llm-evaluation",
  "base_sync_id": "bf2525fe-afbb-4bcd-aa75-61c0b0b75fea",
  "head_sync_id": "f09c868e-09fd-4405-88e3-c3efea430295",
  "summary": "The diff introduces a new RandomForestModel and updates dependencies. The main change is adding seaborn as a dependency, which is not used in the new model code. Other changes are correct additions and modifications.",
  "findings": [
    {
      "severity": "low",
      "path": "pyproject.toml",
      "title": "Unnecessary dependency added",
      "rationale": "The 'seaborn' package is added to dependencies but not used in the new RandomForestModel code. This could be considered an unnecessary dependency.",
      "line_start": 14,
      "line_end": 14
    }
  ]
}
```

You can also use the same capability through `/chat` or `repl` with prompts such
as `Haz una review de la rama new-model-llm-evaluation`.

Note:

- This branch review flow is implemented as a study case to validate the
  product direction.
- Repository and branch synchronization were not originally designed for this
  use case, so the current approach is functional but not the most optimal
  architecture for large-scale or high-frequency review workflows.
- Because this project is designed around a **private LLM setup**, keeping
  repository snapshots in the local filesystem is materially cheaper and faster
  than pushing the same workflow through external hosted infrastructure.
- Privacy is a primary constraint here: the current approach deliberately
  favors keeping repository contents and review execution close to the local
  environment.
- The logical next step would be to add an execution sandbox so the model can
  go beyond static review: generate new code, run the project, validate corner
  cases, execute targeted checks, and test behavioral hypotheses safely.

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
