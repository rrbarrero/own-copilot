import json
import uuid
from pathlib import Path
from typing import Annotated

import httpx
import typer

app = typer.Typer(help="CLI client for testing Own Copilot API.")


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
                # Test idempotency
                typer.echo("\nTesting idempotency (re-sending same key)...")
                response2 = client.post(full_url, headers=headers, files=upload_files)
                typer.echo(f"Status (Retried): {response2.status_code}")
                typer.echo(json.dumps(response2.json(), indent=2))
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


@app.command()
def chat(
    question: Annotated[str, typer.Argument(help="Your question for the copilot")],
    repo_id: Annotated[str | None, typer.Option(help="Filter by repository ID")] = None,
    doc_id: Annotated[str | None, typer.Option(help="Filter by document ID")] = None,
    url: Annotated[str, typer.Option(help="API Base URL")] = "http://localhost:8000",
):
    """
    Query the chatbot with a question and a specific scope.
    """
    full_url = f"{url.rstrip('/')}/chat"

    # Determine scope
    if doc_id:
        scope = {"type": "document", "document_id": doc_id}
    elif repo_id:
        scope = {"type": "repository", "repository_id": repo_id}
    else:
        typer.secho(
            "Error: You must provide either --repo-id or --doc-id to set a scope.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    payload = {
        "question": question,
        "scope": scope,
    }

    typer.echo(f"Asking: '{question}' (Scope: {scope['type']})")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(full_url, json=payload)

            typer.echo(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                typer.secho("\nAnswer:", fg=typer.colors.BLUE, bold=True)
                typer.echo(data["answer"])

                if data.get("citations"):
                    typer.secho("\nCitations:", fg=typer.colors.YELLOW)
                    for cite in data["citations"]:
                        path = cite["path"]
                        fname = cite["filename"]
                        idx = cite["chunk_index"]
                        msg = f"- {fname} (chunk {idx}) in {path}"
                        typer.echo(msg)
            else:
                typer.echo("Response Body:")
                typer.echo(json.dumps(response.json(), indent=2))
                typer.secho("\nERROR: Chat request failed.", fg=typer.colors.RED)

    except Exception as e:
        typer.secho(f"An error occurred: {e}", fg=typer.colors.RED)


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


if __name__ == "__main__":
    app()
