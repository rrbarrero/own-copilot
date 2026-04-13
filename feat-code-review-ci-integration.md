# Feature: Code Review/Remediation CI Integration

This feature allows the system to review a repository branch against `main`
after synchronizing both branches, computing the diff between their snapshots,
and generating structured findings with **severity**, **affected file**, and **line
range**. The current implementation now also includes a **first remediation flow**:
after the review, the LLM can clone the target branch, apply a fix, commit it,
and push it back to the remote branch while keeping the full execution trace in
stdout. In a CI-oriented workflow, the same capability can later be extended
with stronger sandboxing, remediation agents, and validation stages. The
current approach is based on a **PRIVACY FIRST self-hosted LLM**, following the
set of premises and tradeoffs described later in this document.

## Run the branch review using the repository ID and the target branch name.
```
uv run python scripts/api_client.py review-branch \
  e2196e4e-fc51-46ec-aeff-f56cc36e08cd \
  new-model-llm-evaluation
```

## Example response

This is a real and functional response produced by the current implementation.

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

time uv run python scripts/api_client.py review-branch  new-model-llm-evaluation  0,24s user 0,06s system 2% cpu 14,437 total
```

## Run the remediation flow

Once the review has identified a finding, the current POC can ask the LLM to
apply a fix directly on the reviewed branch:

```bash
uv run python scripts/api_client.py remediate-reviewed-branch \
  e2196e4e-fc51-46ec-aeff-f56cc36e08cd \
  new-model-llm-evaluation
```

## Example remediation response

This is a real response produced by the current implementation.

```json
{
  "repository_id": "e2196e4e-fc51-46ec-aeff-f56cc36e08cd",
  "branch": "new-model-llm-evaluation",
  "review_summary": "The diff introduces a new RandomForestModel and updates dependencies. The main issues are an unnecessary seaborn dependency and potential type checking issues.",
  "remediated_finding_title": "Unnecessary Dependency",
  "commit_sha": "00135df7dacfc3afbcb5a3b593681337c7e664c0",
  "changed_files": [
    "pyproject.toml"
  ]
}
```

## Evidence

- Review remediation commit: `00135df7dacfc3afbcb5a3b593681337c7e664c0`
- The execution trace recorded by the API confirms the following steps:
  `git clone`, `git config`, file read, file write, `git diff`, `git status`,
  `git add`, `git commit`, `git push`, `git rev-parse`.

> [!IMPORTANT]
> Review the exact remediation diff in GitHub:
> [Open commit `00135df`](https://github.com/rrbarrero/credit-fraud/pull/1/changes/00135df7dacfc3afbcb5a3b593681337c7e664c0)

Relevant trace excerpts from the real run:

```text
git clone --branch new-model-llm-evaluation --single-branch https://github.com/rrbarrero/credit-fraud.git /app/storage/sandbox-runs/credit-fraud/new-model-llm-evaluation/3d1ba1cb-7da0-44f6-b7d3-ed96158d677a/repo

git diff -- pyproject.toml
@@ -14,11 +14,10 @@ dependencies = [
     "pydantic-settings>=2.9.1",
     "xgboost>=3.0.2",
     "lightgbm>=4.4.0",
-    "seaborn>=0.13.2",
 ]

git commit -m Remove unused seaborn dependency to reduce package size and attack surface

git push origin new-model-llm-evaluation
To https://github.com/rrbarrero/credit-fraud.git
   e19c52c..00135df  new-model-llm-evaluation -> new-model-llm-evaluation
```

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
- The remediation step is intentionally still narrow in operational scope: it
  is meant to validate the end-to-end loop `review -> fix -> commit -> push`
  before introducing broader repository actions, test execution, or richer
  multi-file planning.

## Tradeoffs

### Pros of a local LLM setup

- In repository-heavy RAG workflows, a local setup makes it easier to keep
  embeddings, indexed chunks, retrieval logic, and repository snapshots close
  to the same execution environment, which reduces integration friction.
- For repeated vectorization and retrieval over the same repositories, the
  marginal **cost is usually lower** than calling an external API for each
  embedding or review-related interaction.
- From a strategic cost perspective, a local setup is also attractive if the
  **market trend continues toward materially more expensive LLM usage** over the
  medium to long term.
- Data locality is also better: the retrieval pipeline can operate near the
  source snapshots, chunk store, and vector index without depending on
  round-trips to external hosted services.
- **Privacy** is a primary constraint here: the current approach deliberately
  favors keeping repository contents and review execution close to the local
  environment.
- Running a **local LLM reduces dependency on third-party infrastructure and
  avoids external API availability issues**, provider-side incidents, and the
  kind of recurring **outages** that frontier services such as Claude can have.
- A local setup gives **stronger control** over model versioning, runtime behavior,
  filesystem integration, and execution flow, which is especially useful for
  repository-centric workflows.
- **Integration with a local sandbox is also more organic and simpler**, because
  the model, repository snapshots, execution environment, and validation tools
  can live close to each other without crossing third-party boundaries.
- In that same sandboxed model, it would be natural to preinstall the SDKs
  required by the target stack, for example Android and iOS/iPhone tooling, so
  the execution environment is closer to the real product context.
- Once the infrastructure is in place, the **marginal cost of repeated** reviews,
  iterative prompts, and repository-heavy workflows is usually much lower than
  with frontier APIs.

### Cons of a local LLM setup

- Local models usually provide lower peak quality than top-tier frontier models 
  for difficult reasoning, nuanced code review, and long-context synthesis, 
  although there are powerful open-weight models specifically designed for 
  coding that can be self-hosted — such as Qwen2.5-Coder-32B, which consistently 
  ranks among the top open-source coding models and is deployable via Ollama on 
  capable hardware.
- A local stack pushes more operational burden onto the project: provisioning
  hardware, managing GPU or CPU limits, tuning performance, handling
  observability, and maintaining the full inference environment.
- Frontier APIs such as Anthropic Claude can still outperform local models on
  instruction-following, depth of reasoning, and robustness on harder review
  tasks, so the tradeoff is not only cost and privacy, but also raw model
  capability.
- In any case, moving from an internal LLM backend to an external one would be
  relatively trivial from an architectural perspective (even a mix of them, for example reflection pattern), 
  because the main value of the system is in the orchestration, retrieval, 
  repository handling, and review workflow around the model rather than in 
  a provider-specific coupling.

## Next Step

- In a CI-oriented integration, the review result could drive follow-up
  automation with explicit policies. For example, only low/medium findings
  could be auto-remediated, while high-severity findings might require manual
  approval before push.
- Even in that model, automatic remediation should be applied conservatively.
  A reasonable policy would be to allow this flow only for `severity: low`
  findings, and only after several controls have passed, such as deterministic
  diff inspection, scoped file access, and targeted validation commands.
- A stronger production-ready variant would also include a human-in-the-loop
  checkpoint before the final push, especially when the agent proposes a code
  change that is not a trivial configuration cleanup.
- That kind of multi-agent workflow would benefit from strong observability, so
  the system can expose the progress of every stage: review, remediation,
  validation, retries, and final outcome.
- Another **idea worth exploring** would be to synchronize repositories in the 
  background on developers' workstations, so the **ingestion process can be 
  partially warmed up in advance by embedding changed files incrementally**. 
  This could reduce latency at review time without blocking the main workflow. 
  Two possible deployment models are worth considering: mounting the repository 
  over an NFS share tunneled through WireGuard, or using a peer-to-peer sync 
  tool such as Syncthing, which would keep a local copy of the repository on 
  each workstation and avoid network latency altogether during the embedding 
  process. Both approaches are **only relevant as a mitigation for severe 
  bottlenecks** in the revision step, and would need to be evaluated against operational 
  complexity and overall cost.

## Steps to reproduce

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
SANDBOX_GITHUB_TOKEN=<token-with-push-permissions>
SANDBOX_GIT_USER_NAME=Own Copilot Bot
SANDBOX_GIT_USER_EMAIL=own-copilot@example.com
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
  --branch new-model-llm-evaluation
```

3. Wait until both sync jobs are completed.

4. Run the review:

```bash
uv run python scripts/api_client.py review-branch \
  <repository_id> \
  new-model-llm-evaluation
```

5. Run the remediation:

```bash
uv run python scripts/api_client.py remediate-reviewed-branch \
  <repository_id> \
  new-model-llm-evaluation
```

### 6. Validate the implementation

Run the non-E2E suite through the project Makefile:

```bash
make test-no-e2e
```
