"""Controlled sample web application for local deployments.

The backend chooses this template. No uploaded archives or arbitrary user code
are executed. The process only serves this page and two fixed JSON endpoints.
"""

import argparse
import html
import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>@@NAME@@ - Mini AWS Sample App</title>
  <style>
    :root { --navy: #232f3e; --orange: #ff9900; --ink: #16191f; --muted: #5f6b7a; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; color: var(--ink); background: #f2f3f3; }
    header { background: var(--navy); color: #fff; padding: 18px 26px; border-bottom: 3px solid var(--orange); display: flex; align-items: center; justify-content: space-between; gap: 18px; }
    .brand { font-weight: 750; }
    .brand span { color: #ffd18a; }
    main { max-width: 920px; margin: 34px auto; padding: 0 18px; }
    .hero { background: #fff; border: 1px solid #d5dbdb; border-radius: 7px; padding: 30px; }
    .eyebrow { color: #687482; font-size: 10px; letter-spacing: .14em; font-weight: 750; }
    h1 { margin: 8px 0 10px; font-size: clamp(28px, 4vw, 42px); letter-spacing: -.04em; }
    .lead { color: var(--muted); line-height: 1.65; max-width: 680px; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 22px; }
    .card { background: #fbfcfd; border: 1px solid #d5dbdb; border-radius: 5px; padding: 17px; }
    .card h2 { margin: 0 0 8px; font-size: 12px; color: #687482; letter-spacing: .07em; text-transform: uppercase; }
    .card strong { font-size: 15px; overflow-wrap: anywhere; }
    .status { display: inline-flex; align-items: center; gap: 6px; color: #176b3a; background: #e8f6ed; border: 1px solid #b7dfc4; border-radius: 999px; padding: 5px 10px; font-size: 12px; }
    .status::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    button { margin-top: 22px; padding: 9px 13px; border: 1px solid #0972d3; border-radius: 4px; background: #0972d3; color: #fff; font: inherit; font-size: 13px; font-weight: 650; cursor: pointer; }
    button:hover { background: #075b9a; }
    footer { color: #687482; text-align: center; font-size: 12px; padding: 24px 10px 40px; }
    @media (max-width: 720px) { .grid { grid-template-columns: 1fr; } .hero { padding: 22px; } }
  </style>
</head>
<body>
  <header><div class="brand">Mini <span>AWS</span> · Local App Deployment</div><span class="status">Running</span></header>
  <main>
    <section class="hero">
      <div class="eyebrow">CONTROLLED SAMPLE WEB APPLICATION</div>
      <h1>@@NAME@@</h1>
      <p class="lead">This page is served by a real local Python process. It is a
      teaching template, not a production cloud application. No uploaded code is
      executed.</p>
      <div class="grid">
        <div class="card"><h2>Deployment ID</h2><strong>@@ID@@</strong></div>
        <div class="card"><h2>Local port</h2><strong>@@PORT@@</strong></div>
        <div class="card"><h2>Worker PID</h2><strong>@@PID@@</strong></div>
        <div class="card"><h2>Template</h2><strong>sample-web-app</strong></div>
        <div class="card"><h2>Started</h2><strong>@@STARTED@@</strong></div>
        <div class="card"><h2>Backend time</h2><strong id="server-time">Loading…</strong></div>
      </div>
      <button id="refresh" type="button">Refresh from app API</button>
    </section>
  </main>
  <footer>Mini AWS local lab · The app is reachable only on 127.0.0.1</footer>
  <script>
    const output = document.getElementById("server-time");
    async function refresh() {
      output.textContent = "Checking…";
      try {
        const response = await fetch("/api/info", { headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();
        output.textContent = new Date(data.server_time).toLocaleString();
      } catch (error) {
        output.textContent = "Unavailable";
      }
    }
    document.getElementById("refresh").addEventListener("click", refresh);
    refresh();
  </script>
</body>
</html>
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini AWS controlled sample app")
    parser.add_argument("--instance-id", type=int, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--instance-dir", required=True)
    args = parser.parse_args()

    instance_dir = Path(args.instance_dir).resolve()
    instance_dir.mkdir(parents=True, exist_ok=True)
    stop_file = instance_dir / "stop.request"
    worker_file = instance_dir / "worker.json"
    started_at = utc_now()
    started_monotonic = time.monotonic()
    safe_name = html.escape(args.name, quote=False)
    page = (
        PAGE_TEMPLATE.replace("@@NAME@@", safe_name)
        .replace("@@ID@@", str(args.instance_id))
        .replace("@@PORT@@", str(args.port))
        .replace("@@PID@@", str(os.getpid()))
        .replace("@@STARTED@@", html.escape(started_at))
    )

    def worker_payload(status: str) -> dict:
        return {
            "instance_id": args.instance_id,
            "name": args.name,
            "pid": os.getpid(),
            "port": args.port,
            "status": status,
            "started_at": started_at,
            "heartbeat_at": utc_now(),
            "uptime_seconds": max(0, int(time.monotonic() - started_monotonic)),
        }

    class Handler(BaseHTTPRequestHandler):
        server_version = "MiniAWSAppRunner/1.0"

        def _send(self, status_code: int, content_type: str, body: bytes) -> None:
            self.send_response(status_code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (stdlib handler naming)
            path = urlsplit(self.path).path
            if path == "/health":
                payload = {
                    "status": "ok",
                    "service": "mini-aws-sample-application",
                    "instance_id": args.instance_id,
                    "template": "sample-web-app",
                    "pid": os.getpid(),
                    "local_process_not_vm": True,
                }
                self._send(200, "application/json; charset=utf-8", json.dumps(payload).encode())
                return
            if path == "/api/info":
                payload = {
                    "deployment_id": args.instance_id,
                    "name": args.name,
                    "template": "sample-web-app",
                    "pid": os.getpid(),
                    "port": args.port,
                    "started_at": started_at,
                    "server_time": utc_now(),
                    "uptime_seconds": max(0, int(time.monotonic() - started_monotonic)),
                }
                self._send(200, "application/json; charset=utf-8", json.dumps(payload).encode())
                return
            if path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))
                return
            if path == "/favicon.ico":
                self._send(204, "image/x-icon", b"")
                return
            self._send(
                404,
                "application/json; charset=utf-8",
                json.dumps({"error": "not_found"}).encode(),
            )

        def log_message(self, format: str, *args) -> None:
            print(f"[{utc_now()}] {self.address_string()} {format % args}", flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    write_json_atomic(worker_file, worker_payload("running"))
    print(
        f"[app] deployment {args.instance_id} listening on http://127.0.0.1:{args.port}/",
        flush=True,
    )

    try:
        while not stop_file.exists():
            write_json_atomic(worker_file, worker_payload("running"))
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[app] interrupted", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        stop_file.unlink(missing_ok=True)
        worker_file.unlink(missing_ok=True)
        print(f"[app] deployment {args.instance_id} stopped", flush=True)


if __name__ == "__main__":
    main()
