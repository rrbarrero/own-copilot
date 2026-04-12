import json
import uuid
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer

app = typer.Typer(help="CLI client for testing Own Copilot API.")

# Local file to persist the last conversation ID for a seamless experience
LAST_CONV_FILE = Path(".last_conversation_id")


def get_last_conversation_id() -> str | None:
    if LAST_CONV_FILE.exists():
        return LAST_CONV_FILE.read_text().strip()
    return None


def save_last_conversation_id(conv_id: str):
    LAST_CONV_FILE.write_text(str(conv_id))


@app.command()
def upload(
    files: Annotated[list[Path], typer.Argument(help="Files to upload")],
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Test individual file upload with idempotency check.
    """
    idempotency_key = str(uuid.uuid4())
    typer.echo(f"Using Idempotency-Key: {idempotency_key}")

    full_url = f"{url.rstrip('/')}/ingestion/upload"
    headers = {"X-Idempotency-Key": idempotency_key}

    upload_files = []
    for path in files:
        if not path.exists():
            typer.secho(f"Error: file {path} does not exist.", fg=typer.colors.RED)
            continue
        upload_files.append(("files", (path.name, path.read_bytes())))

    if not upload_files:
        typer.echo("No valid files to upload.")
        raise typer.Exit(code=1)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(full_url, headers=headers, files=upload_files)

            typer.echo(f"Status: {response.status_code}")
            typer.echo("Response Body:")
            typer.echo(json.dumps(response.json(), indent=2))

            if response.status_code == 200:
                typer.secho("\nOK: Upload successful.", fg=typer.colors.GREEN)
            else:
                typer.secho("\nERROR: Upload failed.", fg=typer.colors.RED)

    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def sync_repo(
    clone_url: Annotated[str, typer.Argument(help="GitHub clone URL")],
    branch: Annotated[str | None, typer.Option(help="Branch to sync")] = None,
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Test repository synchronization endpoint.
    """
    full_url = f"{url.rstrip('/')}/repositories/sync"
    payload = {"clone_url": clone_url, "branch": branch}

    typer.echo(f"Requesting sync for: {clone_url} (branch: {branch or 'default'})")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(full_url, json=payload)

            typer.echo(f"Status: {response.status_code}")
            typer.echo("Response Body:")
            typer.echo(json.dumps(response.json(), indent=2))

            if response.status_code == 200:
                typer.secho("\nOK: Sync request accepted.", fg=typer.colors.GREEN)
            else:
                typer.secho("\nERROR: Sync request failed.", fg=typer.colors.RED)

    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


def _do_chat(
    client: httpx.Client,
    full_url: str,
    question: str,
    scope: dict[str, Any],
    conv_id: str | None,
) -> str | None:
    payload = {
        "question": question,
        "scope": scope,
        "conversation_id": conv_id,
    }

    response = client.post(full_url, json=payload)

    if response.status_code == 200:
        data = response.json()
        new_id = data.get("conversation_id")
        if new_id:
            save_last_conversation_id(new_id)

        typer.secho("\nAnswer:", fg=typer.colors.BLUE, bold=True)
        typer.echo(data["answer"])

        if data.get("citations"):
            typer.secho("\nCitations:", fg=typer.colors.YELLOW)
            for cite in data["citations"]:
                # Multi-line string to satisfy Ruff E501
                msg = (
                    f"- {cite.get('filename')} "
                    f"(chunk {cite.get('chunk_index')}) in {cite.get('path')}"
                )
                typer.echo(msg)
        return new_id

    # Breaking long line to satisfy Ruff E501
    err_msg = f"\nERROR ({response.status_code}): {response.text}"
    typer.secho(err_msg, fg=typer.colors.RED)
    return None


@app.command()
def chat(
    question: Annotated[str, typer.Argument(help="Your question for the copilot")],
    repo_id: Annotated[str | None, typer.Option(help="Filter by repository ID")] = None,
    repo_sync_id: Annotated[
        str | None, typer.Option(help="Filter by repository sync ID")
    ] = None,
    doc_id: Annotated[str | None, typer.Option(help="Filter by document ID")] = None,
    conv_id: Annotated[
        str | None, typer.Option(help="Specific conversation ID")
    ] = None,
    new: Annotated[
        bool, typer.Option("--new", help="Start a new conversation")
    ] = False,
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Query the chatbot with a question. History is tracked automatically.
    """
    full_url = f"{url.rstrip('/')}/chat"

    # Use specified conv_id, or persisted last one, unless --new is set
    last_id = get_last_conversation_id()
    effective_conv_id = conv_id if conv_id else (None if new else last_id)

    # Determine scope
    if doc_id:
        scope = {"type": "document", "document_id": doc_id}
    elif repo_id:
        scope = {
            "type": "repository",
            "repository_id": repo_id,
            "repository_sync_id": repo_sync_id,
        }
    else:
        typer.secho(
            "Error: Scope required (use --repo-id or --doc-id).", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    try:
        with httpx.Client(timeout=60.0 * 3) as client:
            _do_chat(client, full_url, question, scope, effective_conv_id)
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def repl(
    repo_id: Annotated[str | None, typer.Option(help="Filter by repository ID")] = None,
    repo_sync_id: Annotated[
        str | None, typer.Option(help="Filter by repository sync ID")
    ] = None,
    doc_id: Annotated[str | None, typer.Option(help="Filter by document ID")] = None,
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Interactive chat session (REPL mode).
    """
    full_url = f"{url.rstrip('/')}/chat"

    if not repo_id and not doc_id:
        typer.secho(
            "Error: You must provide --repo-id or --doc-id to start.",
            fg=typer.colors.RED,
        )
        return

    scope = (
        {"type": "document", "document_id": doc_id}
        if doc_id
        else {
            "type": "repository",
            "repository_id": repo_id,
            "repository_sync_id": repo_sync_id,
        }
    )
    conv_id = None

    typer.secho(
        "--- Entering Interactive Mode (type 'exit' or 'quit' to stop) ---",
        fg=typer.colors.MAGENTA,
    )

    with httpx.Client(timeout=60.0 * 3) as client:
        while True:
            question = typer.prompt("Copilot >>")
            if question.lower() in ["exit", "quit"]:
                break

            conv_id = _do_chat(client, full_url, question, scope, conv_id)
            typer.echo("-" * 40)


@app.command()
def list_repos(
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    List all synchronized repositories.
    """
    full_url = f"{url.rstrip('/')}/repositories"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(full_url)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    typer.echo("No repositories found.")
                    return
                typer.secho("\nRepositories:", fg=typer.colors.CYAN, bold=True)
                for repo in data:
                    typer.echo(f"- {repo['owner']}/{repo['name']} (ID: {repo['id']})")
            else:
                typer.secho(f"Error: {response.status_code}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def list_docs(
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    List all processed documents.
    """
    full_url = f"{url.rstrip('/')}/documents"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(full_url)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    typer.echo("No documents found.")
                    return
                typer.secho("\nDocuments:", fg=typer.colors.CYAN, bold=True)
                for doc in data:
                    typer.echo(f"- {doc['filename']} (ID: {doc['id']})")
            else:
                typer.secho(f"Error: {response.status_code}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def resolve_branch(
    repository_id: Annotated[str, typer.Argument(help="Repository ID")],
    branch: Annotated[str, typer.Argument(help="Branch to resolve")],
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Resolve the latest completed sync for a repository branch.
    """
    full_url = f"{url.rstrip('/')}/repositories/resolve-branch"
    payload = {"repository_id": repository_id, "branch": branch}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(full_url, json=payload)
            typer.echo(f"Status: {response.status_code}")
            typer.echo("Response Body:")
            typer.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def review_branch(
    repository_id: Annotated[str, typer.Argument(help="Repository ID")],
    branch: Annotated[str, typer.Argument(help="Branch to review against main")],
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Request a review for a branch against main.
    """
    full_url = f"{url.rstrip('/')}/repositories/review"
    payload = {"repository_id": repository_id, "branch": branch}

    try:
        with httpx.Client(timeout=60.0 * 3) as client:
            response = client.post(full_url, json=payload)
            typer.echo(f"Status: {response.status_code}")
            typer.echo("Response Body:")
            typer.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


@app.command()
def remediate_reviewed_branch(
    repository_id: Annotated[str, typer.Argument(help="Repository ID")],
    branch: Annotated[str, typer.Argument(help="Branch to remediate in sandbox")],
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Run the demo sandbox remediation flow for a reviewed branch.
    """
    full_url = f"{url.rstrip('/')}/repositories/remediate-reviewed-branch"
    payload = {"repository_id": repository_id, "branch": branch}

    try:
        with httpx.Client(timeout=60.0 * 5) as client:
            response = client.post(full_url, json=payload)
            typer.echo(f"Status: {response.status_code}")
            typer.echo("Response Body:")
            typer.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
