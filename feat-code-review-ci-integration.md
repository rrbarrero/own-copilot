# Feature: Code Review CI Integration

This feature allows the system to review a repository branch against `main`
after synchronizing both branches, computing the diff between their snapshots,
and generating structured findings with severity, affected file, and line
range. In a CI-oriented workflow, the same capability can be used as an
automated review step before merge, and later extended with sandboxed
execution, remediation agents, and validation stages.

## Run the branch review using the repository ID and the target branch name.
```
uv run python scripts/api_client.py review-branch \
  e2196e4e-fc51-46ec-aeff-f56cc36e08cd \
  new-feature-branch
```

## Example response

This is a real and functional response produced by the current implementation.

```json
{
  "repository_id": "e2196e4e-fc51-46ec-aeff-f56cc36e08cd",
  "base_branch": "main",
  "branch": "new-feature-branch",
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

## Notes

- This branch review flow is implemented as a study case to validate the
  product direction.
- The example shown here was executed on a low-end GPU setup, specifically an
  NVIDIA RTX 3070 Ti with 8 GB of VRAM, so the model used in practice was
  chosen as a validation vehicle for the idea rather than as the strongest
  possible model for the task.
- It is an adaptation built on top of the architecture that already existed in
  the project to make room for this feature.
- Repository and branch synchronization were not originally designed for this
  use case, so the implementation works, but it is not the cleanest or most
  optimal design for supporting branch review as a first-class capability.
- In other words, this feature was integrated pragmatically into the current
  system rather than introduced through a dedicated architecture designed for it
  from the beginning.

## Tradeoffs

### Pros of a local LLM setup

- In repository-heavy RAG workflows, a local setup makes it easier to keep
  embeddings, indexed chunks, retrieval logic, and repository snapshots close
  to the same execution environment, which reduces integration friction.
- For repeated vectorization and retrieval over the same repositories, the
  marginal cost is usually lower than calling an external API for each
  embedding or review-related interaction.
- Data locality is also better: the retrieval pipeline can operate near the
  source snapshots, chunk store, and vector index without depending on
  round-trips to external hosted services.
- Privacy is a primary constraint here: the current approach deliberately
  favors keeping repository contents and review execution close to the local
  environment.
- Running a local LLM reduces dependency on third-party infrastructure and
  avoids external API availability issues, provider-side incidents, and the
  kind of recurring outages that frontier services such as Claude can have.
- A local setup gives stronger control over model versioning, runtime behavior,
  filesystem integration, and execution flow, which is especially useful for
  repository-centric workflows.
- Integration with a local sandbox is also more organic and simpler, because
  the model, repository snapshots, execution environment, and validation tools
  can live close to each other without crossing third-party boundaries.
- Once the infrastructure is in place, the marginal cost of repeated reviews,
  iterative prompts, and repository-heavy workflows is usually much lower than
  with frontier APIs.

### Cons of a local LLM setup

- Local models usually provide lower peak quality than top-tier frontier models
  for difficult reasoning, nuanced code review, and long-context synthesis.
- A local stack pushes more operational burden onto the project: provisioning
  hardware, managing GPU or CPU limits, tuning performance, handling
  observability, and maintaining the full inference environment.
- Frontier APIs such as Anthropic Claude can still outperform local models on
  instruction-following, depth of reasoning, and robustness on harder review
  tasks, so the tradeoff is not only cost and privacy, but also raw model
  capability.
- In any case, moving from an internal LLM backend to an external one would be
  relatively trivial from an architectural perspective, because the main value
  of the system is in the orchestration, retrieval, repository handling, and
  review workflow around the model rather than in a provider-specific coupling.

## Next Step

- The logical next step would be to add an execution sandbox so the model can
  go beyond static review: generate new code, run the project, validate corner
  cases, execute targeted checks, and test behavioral hypotheses safely.
- In a CI-oriented integration, the review result could also drive follow-up
  automation. For example, depending on the severity of a finding, another
  agent could be responsible for attempting a fix, validating it, and pushing
  a new update back to the branch.
- That kind of multi-agent workflow would benefit from strong observability, so
  the system can expose the progress of every stage: review, remediation,
  validation, retries, and final outcome.

## Reproduce

### 1. Clone the repository

```bash
git clone https://github.com/rrbarrero/own-copilot.git
cd own-copilot
```

### 2. Configure the environment

Create a local `.env` from `.env.example`:

```bash
cp .env.example .env
```

At minimum, verify these values:

```env
DEBUG=false
DATABASE_URL=postgres://postgres:postgres@db:5432/postgres?sslmode=disable
STORAGE_PATH=/app/storage
OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen3-8b-12k:latest
EMBEDDING_MODEL=bge-m3:latest
LLM_TEMPERATURE=0.0
RAPTOR_ENABLED=true
RAPTOR_MAX_UNITS_PER_DOCUMENT=2
RAPTOR_MAX_UNIT_CHARS=1500
```

If Ollama is not reachable through `host.docker.internal` in your environment,
replace `OLLAMA_BASE_URL` with the correct URL for the machine running Ollama.

### 3. Start the stack with Docker

```bash
docker compose up --build
```

This starts the API, worker, and database through Docker.

### 4. Verify that Ollama is ready

Make sure the selected models are available locally before running the flow.

```bash
ollama list
```

### 5. Run the code review flow

1. Synchronize the default branch:

```bash
uv run python scripts/api_client.py sync-repo https://github.com/rrbarrero/credit-fraud.git
```

2. Synchronize the branch you want to review:

```bash
uv run python scripts/api_client.py sync-repo \
  https://github.com/rrbarrero/credit-fraud.git \
  --branch new-feature-branch
```

3. Wait until both sync jobs are completed.

4. Run the review:

```bash
uv run python scripts/api_client.py review-branch \
  <repository_id> \
  new-feature-branch
```

### 6. Validate the implementation

Run the non-E2E suite through the project Makefile:

```bash
make test-no-e2e
```
