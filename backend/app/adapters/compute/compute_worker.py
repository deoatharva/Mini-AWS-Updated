"""Controlled local compute worker.

This is a small HTTP server that proves the compute instance is a real local
process. It is intentionally not a virtual machine and cannot execute arbitrary
commands or serve arbitrary files.
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini AWS local compute worker")
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
    name = html.escape(args.name, quote=True)

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
        server_version = "MiniAWSWorker/1.0"

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
                    "service": "mini-aws-local-compute-worker",
                    "instance_id": args.instance_id,
                    "pid": os.getpid(),
                    "uptime_seconds": max(0, int(time.monotonic() - started_monotonic)),
                    "local_process_not_vm": True,
                }
                self._send(
                    200,
                    "application/json; charset=utf-8",
                    json.dumps(payload).encode("utf-8"),
                )
                return

            if path in ("/", "/index.html"):
                body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mini AWS instance {args.instance_id}</title>
  <style>
    body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #f2f3f3; color: #16191f; }}
    header {{ background: #232f3e; color: #fff; padding: 16px 24px; border-bottom: 3px solid #ff9900; }}
    main {{ max-width: 760px; margin: 40px auto; background: #fff; border: 1px solid #d5dbdb; border-radius: 6px; padding: 28px; }}
    .eyebrow {{ color: #687482; font-size: 11px; letter-spacing: .12em; font-weight: 700; }}
    h1 {{ margin: 8px 0 14px; font-size: 28px; }}
    .badge {{ display: inline-block; background: #e8f6ed; color: #176b3a; border: 1px solid #b7dfc4; border-radius: 4px; padding: 6px 10px; font-size: 12px; }}
    dl {{ display: grid; grid-template-columns: 160px 1fr; gap: 10px 16px; margin: 24px 0; font-size: 14px; }}
    dt {{ color: #687482; font-weight: 600; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    p {{ color: #5f6b7a; line-height: 1.6; font-size: 14px; }}
  </style>
</head>
<body>
  <header><strong>Mini AWS</strong> &middot; Local Compute</header>
  <main>
    <div class="eyebrow">LOCAL PROCESS INSTANCE</div>
    <h1>{name}</h1>
    <span class="badge">&#9679; Running</span>
    <dl>
      <dt>Instance ID</dt><dd>{args.instance_id}</dd>
      <dt>Worker PID</dt><dd>{os.getpid()}</dd>
      <dt>Local port</dt><dd>{args.port}</dd>
      <dt>Started</dt><dd>{html.escape(started_at)}</dd>
      <dt>Resource type</dt><dd>Python worker process (not a virtual machine)</dd>
    </dl>
    <p>This page is served by a real process on this computer. It is a learning
    resource, not an AWS EC2 instance, and it has no cloud networking or billing.</p>
  </main>
</body>
</html>
"""
                self._send(200, "text/html; charset=utf-8", body.encode("utf-8"))
                return

            self._send(
                404,
                "application/json; charset=utf-8",
                json.dumps({"error": "not_found"}).encode("utf-8"),
            )

        def log_message(self, format: str, *args) -> None:
            print(f"[{utc_now()}] {self.address_string()} {format % args}", flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    write_json_atomic(worker_file, worker_payload("running"))
    print(
        f"[worker] instance {args.instance_id} listening on http://127.0.0.1:{args.port}/",
        flush=True,
    )

    try:
        while not stop_file.exists():
            write_json_atomic(worker_file, worker_payload("running"))
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[worker] interrupted", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        stop_file.unlink(missing_ok=True)
        worker_file.unlink(missing_ok=True)
        print(f"[worker] instance {args.instance_id} stopped", flush=True)


if __name__ == "__main__":
    main()
