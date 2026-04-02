import os
import sys
import time
import urllib.error
import urllib.request


def wait_http(name: str, urls: list[str], timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""

    while time.time() < deadline:
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    if 200 <= resp.status < 500:
                        print(f"[wait] {name} ready: {url} ({resp.status})")
                        return
            except urllib.error.URLError as exc:
                last_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)

        time.sleep(2)

    raise RuntimeError(f"{name} not ready within {timeout_seconds}s. Last error: {last_error}")


def main() -> int:
    chroma_host = os.getenv("CHROMA_HOST", "chromadb")
    chroma_port = os.getenv("CHROMA_PORT", "8001")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")

    chroma_urls = [
        f"http://{chroma_host}:{chroma_port}/api/v1/heartbeat",
        f"http://{chroma_host}:{chroma_port}/api/v2/heartbeat",
    ]
    ollama_urls = [
        f"{ollama_base_url}/api/tags",
        f"{ollama_base_url}/",
    ]

    print("[wait] waiting for ChromaDB...")
    wait_http("chromadb", chroma_urls, timeout_seconds=180)
    print("[wait] waiting for Ollama...")
    wait_http("ollama", ollama_urls, timeout_seconds=300)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[wait] dependency check failed: {exc}", file=sys.stderr)
        raise
