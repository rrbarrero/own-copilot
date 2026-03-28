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


if __name__ == "__main__":
    app()
