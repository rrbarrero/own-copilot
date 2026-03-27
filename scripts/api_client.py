import argparse
import uuid
from pathlib import Path

import httpx


def test_upload(url: str, files_paths: list[str]):
    idempotency_key = str(uuid.uuid4())
    print(f"Using Idempotency-Key: {idempotency_key}")

    full_url = f"{url.rstrip('/')}/ingestion/upload"
    headers = {"X-Idempotency-Key": idempotency_key}

    files = []
    for p in files_paths:
        path = Path(p)
        if not path.exists():
            print(f"Error: file {p} does not exist.")
            continue
        files.append(("files", (path.name, path.read_bytes())))

    if not files:
        print("No files to upload.")
        return

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(full_url, headers=headers, files=files)

            print(f"Status: {response.status_code}")
            print("Response Body:")
            import json

            print(json.dumps(response.json(), indent=2))

            if response.status_code == 200:
                print("\nOK: Upload successful.")
                # Test idempotency
                print("\nTesting idempotency (re-sending same key)...")
                response2 = client.post(full_url, headers=headers, files=files)
                print(f"Status (Retried): {response2.status_code}")
                print(json.dumps(response2.json(), indent=2))
            else:
                print("\nERROR: Upload failed.")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test manual file upload.")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Base URL of the API"
    )
    parser.add_argument(
        "files", nargs="*", help="File paths to upload (default: creates 2 dummy files)"
    )

    args = parser.parse_args()

    files_to_upload = args.files
    if not files_to_upload:
        # Create dummy files if none provided
        print("No files provided, creating dummy files...")
        f1 = Path("/tmp/test1.txt")
        f1.write_text("Hello from file 1")
        f2 = Path("/tmp/test2.txt")
        f2.write_text("Hello from file 2")
        files_to_upload = [str(f1), str(f2)]

    test_upload(args.url, files_to_upload)
