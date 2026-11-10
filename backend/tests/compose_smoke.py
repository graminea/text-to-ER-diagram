"""Exercise the packaged services through Compose with a local provider."""

import json
import subprocess
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, Thread
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from uuid import uuid4

from tests.support import EXAMPLE_REQUIREMENTS, example_schema

SLOW_SUCCESS = f"{EXAMPLE_REQUIREMENTS} Simule uma resposta lenta e válida."
SLOW_TIMEOUT = f"{EXAMPLE_REQUIREMENTS} Simule um tempo limite excedido."


class Provider(BaseHTTPRequestHandler):
    calls: list[str] = []
    reviews = Barrier(2, timeout=8)

    def do_POST(self):
        assert self.path == "/v1/chat/completions"
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        schema = request["response_format"]["json_schema"]["name"]
        self.calls.append(schema)
        requirements = request["messages"][-1]["content"]
        if requirements == SLOW_TIMEOUT:
            sleep(20)
            return
        if requirements == SLOW_SUCCESS:
            # Exceed Nginx's default read timeout while staying within the API budget.
            sleep(62)
        if schema == "er_review":
            self.reviews.wait()
        payload = {"findings": []} if schema == "er_review" else example_schema()
        choice = {
            "index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(payload)},
        }
        reply = {
            "id": "offline", "created": 1, "model": "gpt-4o-mini",
            "object": "chat.completion", "choices": [choice],
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(reply).encode())


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("src"):
            self.scripts.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "stylesheet" and attributes.get("href"):
            self.stylesheets.append(attributes["href"])


def request(url, payload=None, *, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def verify_web(base):
    page = request(f"{base}/").decode()
    assert "<title>Text to ER</title>" in page
    assets = Assets()
    assets.feed(page)
    assert assets.scripts and assets.stylesheets, "Frontend HTML is missing JS or CSS"
    for paths, media_types in (
        (assets.scripts, ("application/javascript", "text/javascript")),
        (assets.stylesheets, ("text/css",)),
    ):
        for path in paths:
            url = urljoin(f"{base}/", path)
            assert url.startswith(f"{base}/"), f"Asset is not same-origin: {path}"
            with urlopen(url, timeout=10) as response:
                assert response.headers.get_content_type() in media_types, path
                assert response.read(1), f"Asset is empty: {path}"
    for path in ("/docs", "/redoc", "/openapi.json"):
        try:
            request(base + path)
        except HTTPError as error:
            with error:
                assert error.code == 404, path
        else:
            raise AssertionError(f"{path} is publicly available")
    assert json.loads(request(f"{base}/api/health"))["status"] == "ok"


def verify_generations(url):
    ids = set()
    flows = {
        "A": ["conceptual_er"],
        "B": ["conceptual_er", "er_review", "er_review", "conceptual_er"],
    }
    for flow, expected in flows.items():
        Provider.calls.clear()
        requirements = SLOW_SUCCESS if flow == "A" else EXAMPLE_REQUIREMENTS
        started = monotonic()
        result = json.loads(request(url, {"flow": flow, "requirements": requirements}, timeout=100))
        if flow == "A":
            assert monotonic() - started > 60, "Slow generation returned before the proxy deadline"
        assert Provider.calls == expected, Provider.calls
        assert result["flow"] == flow and result["call_count"] == len(expected)
        assert result["schema_model"] == example_schema() and result["validation"]["valid"]
        ids.add(result["id"])
    return ids


def verify_timeout(url):
    try:
        request(url, {"flow": "A", "requirements": SLOW_TIMEOUT})
    except HTTPError as error:
        with error:
            assert error.code == 504 and json.load(error)["detail"]["code"] == "timeout"
    else:
        raise AssertionError("Slow provider request unexpectedly succeeded")


def main():
    root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory() as tmp, ThreadingHTTPServer(("0.0.0.0", 0), Provider) as provider:
        override = Path(tmp) / "compose.yaml"
        def configure(timeout):
            override.write_text(f"""services:
  api:
    env_file: !reset []
    environment:
      MODEL: openai/gpt-4o-mini
      API_KEY: test-only
      API_BASE: http://host.docker.internal:{provider.server_port}/v1
      TIMEOUT: "{timeout}"
  web:
    ports: !override ["127.0.0.1::8080"]
""", encoding="utf-8")
        command = [
            "docker", "compose", "-p", f"er-smoke-{uuid4().hex[:8]}",
            "-f", str(root / "compose.yaml"), "-f", str(override),
        ]

        def compose(*args, capture=False):
            return subprocess.run([*command, *args], check=True, capture_output=capture, text=True)

        def web_url():
            address = compose("port", "web", "8080", capture=True).stdout.strip()
            return f"http://{address}"

        Thread(target=provider.serve_forever, daemon=True).start()
        try:
            configure(timeout=90)
            compose("up", "--build", "--wait", "--wait-timeout", "120")
            base = web_url()
            verify_web(base)
            api = compose("ps", "-q", "api", capture=True).stdout.strip()
            bindings = subprocess.check_output(
                ["docker", "inspect", "--format", "{{json .HostConfig.PortBindings}}", api],
                text=True,
            )
            assert not json.loads(bindings), "The API is published directly on the host"
            ids = verify_generations(f"{base}/api/generations")
            compose("down")
            configure(timeout=15)
            compose("up", "--wait", "--wait-timeout", "120")
            url = f"{web_url()}/api/generations"
            verify_timeout(url)
            assert {generation["id"] for generation in json.loads(request(url))} == ids
        finally:
            provider.shutdown()
            compose("down", "--volumes", "--rmi", "local")


if __name__ == "__main__":
    main()
