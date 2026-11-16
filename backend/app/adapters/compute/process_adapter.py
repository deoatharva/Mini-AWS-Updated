from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path

import psutil


class ComputeAdapterError(RuntimeError):
    """A real local process operation failed."""


@dataclass(frozen=True)
class WorkerInfo:
    instance_id: int
    name: str
    pid: int
    port: int
    status: str
    started_at: str
    heartbeat_at: str
    uptime_seconds: int


class ProcessComputeAdapter:
    """Manage a real local Python worker process for one compute instance."""

    adapter_name = "process"
    heartbeat_max_age_seconds = 10.0
    default_start_timeout = 8.0
    default_stop_timeout = 6.0

    def __init__(
        self,
        instances_dir: Path,
        port_start: int,
        port_end: int,
        worker_script: Path | None = None,
    ) -> None:
        self.instances_dir = Path(instances_dir).resolve()
        self.port_start = port_start
        self.port_end = port_end
        self.worker_script = (
            Path(worker_script).resolve()
            if worker_script is not None
            else Path(__file__).resolve().with_name("compute_worker.py")
        )

    def instance_dir(self, instance_id: int) -> Path:
        if instance_id < 1:
            raise ValueError("Instance ID must be positive.")
        path = (self.instances_dir / str(instance_id)).resolve()
        try:
            path.relative_to(self.instances_dir)
        except ValueError as exc:
            raise ValueError("Instance directory is outside the managed data directory.") from exc
        return path

    def log_path(self, instance_id: int) -> Path:
        return self.instance_dir(instance_id) / "instance.log"

    def _worker_path(self, instance_id: int) -> Path:
        return self.instance_dir(instance_id) / "worker.json"

    def _stop_path(self, instance_id: int) -> Path:
        return self.instance_dir(instance_id) / "stop.request"

    def read_worker_info(self, instance_id: int) -> WorkerInfo | None:
        path = self._worker_path(instance_id)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return WorkerInfo(
                instance_id=int(raw["instance_id"]),
                name=str(raw.get("name") or ""),
                pid=int(raw["pid"]),
                port=int(raw["port"]),
                status=str(raw.get("status") or ""),
                started_at=str(raw.get("started_at") or ""),
                heartbeat_at=str(raw.get("heartbeat_at") or ""),
                uptime_seconds=int(raw.get("uptime_seconds") or 0),
            )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def heartbeat_age(self, info: WorkerInfo) -> float | None:
        try:
            heartbeat = datetime.fromisoformat(info.heartbeat_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()

    def is_heartbeat_fresh(self, info: WorkerInfo | None) -> bool:
        if info is None:
            return False
        age = self.heartbeat_age(info)
        return age is not None and age <= self.heartbeat_max_age_seconds

    def is_process_alive(self, pid: int | None, instance_id: int) -> bool:
        if not pid or pid < 1:
            return False
        try:
            process = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

        try:
            command_line = process.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

        expected_worker = os.path.normcase(str(self.worker_script))
        worker_matches = False
        for argument in command_line:
            try:
                if os.path.normcase(os.path.abspath(argument)) == expected_worker:
                    worker_matches = True
                    break
            except OSError:
                continue
        if not worker_matches:
            return False

        try:
            marker = command_line.index("--instance-id")
            return command_line[marker + 1] == str(instance_id)
        except (ValueError, IndexError):
            return False

    def is_healthy(self, instance_id: int, port: int, timeout: float = 1.2) -> bool:
        connection = HTTPConnection("127.0.0.1", port, timeout=timeout)
        try:
            connection.request("GET", "/health")
            response = connection.getresponse()
            if response.status != 200:
                return False
            payload = json.loads(response.read(4096).decode("utf-8"))
            return (
                payload.get("status") == "ok"
                and int(payload.get("instance_id", -1)) == instance_id
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        finally:
            connection.close()

    def allocate_port(self) -> int:
        for port in range(self.port_start, self.port_end + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.bind(("127.0.0.1", port))
                except OSError:
                    continue
                return port
        raise ComputeAdapterError(
            f"No free local port is available in the configured range "
            f"{self.port_start}-{self.port_end}."
        )

    def start(self, instance_id: int, name: str) -> WorkerInfo:
        directory = self.instance_dir(instance_id)
        directory.mkdir(parents=True, exist_ok=True)
        self._stop_path(instance_id).unlink(missing_ok=True)
        self._worker_path(instance_id).unlink(missing_ok=True)
        log_path = self.log_path(instance_id)
        log_path.write_text("", encoding="utf-8")

        if not self.worker_script.is_file():
            raise ComputeAdapterError("The managed worker script is missing.")

        port = self.allocate_port()
        command = [
            sys.executable,
            "-u",
            str(self.worker_script),
            "--instance-id",
            str(instance_id),
            "--name",
            name,
            "--port",
            str(port),
            "--instance-dir",
            str(directory),
        ]
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        creation_flags = 0
        if os.name == "nt":
            creation_flags = (
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            )

        try:
            with open(log_path, "ab", buffering=0) as log_file:
                process = subprocess.Popen(
                    command,
                    cwd=str(directory),
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    creationflags=creation_flags,
                    close_fds=True,
                )
        except OSError as exc:
            raise ComputeAdapterError(f"Could not start the local worker: {exc}") from exc

        deadline = time.monotonic() + self.default_start_timeout
        while time.monotonic() < deadline:
            info = self.read_worker_info(instance_id)
            if (
                info is not None
                and info.status == "running"
                and self.is_process_alive(info.pid, instance_id)
                and self.is_heartbeat_fresh(info)
                and self.is_healthy(instance_id, info.port)
            ):
                return info

            exit_code = process.poll()
            if exit_code is not None:
                # A venv launcher can exit after spawning the real worker. Only
                # fail when there is no live worker behind it.
                info = self.read_worker_info(instance_id)
                if info is None or not self.is_process_alive(info.pid, instance_id):
                    hint = self._last_log_line(instance_id)
                    raise ComputeAdapterError(
                        f"The local worker exited with code {exit_code}."
                        + (f" {hint}" if hint else "")
                    )
            time.sleep(0.2)

        info = self.read_worker_info(instance_id)
        if info is not None:
            self._terminate_pid(info.pid, instance_id)
        self._terminate_pid(process.pid, instance_id)
        hint = self._last_log_line(instance_id)
        raise ComputeAdapterError(
            "The local worker did not become healthy in time."
            + (f" {hint}" if hint else "")
        )

    def stop(self, instance_id: int, pid: int | None, timeout: float | None = None) -> bool:
        info = self.read_worker_info(instance_id)
        actual_pid = info.pid if info is not None and info.instance_id == instance_id else pid

        if not actual_pid or not self.is_process_alive(actual_pid, instance_id):
            self._cleanup_run_files(instance_id)
            return True

        try:
            self._stop_path(instance_id).write_text("stop", encoding="utf-8")
        except OSError:
            pass

        deadline = time.monotonic() + (timeout or self.default_stop_timeout)
        while time.monotonic() < deadline:
            if not self.is_process_alive(actual_pid, instance_id):
                self._cleanup_run_files(instance_id)
                return True
            time.sleep(0.2)

        self._terminate_pid(actual_pid, instance_id)
        if self._wait_for_exit(actual_pid, instance_id, 3.0):
            self._cleanup_run_files(instance_id)
            return True
        return False

    def _terminate_pid(self, pid: int, instance_id: int) -> None:
        if not self.is_process_alive(pid, instance_id):
            return
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass

    def _wait_for_exit(self, pid: int, instance_id: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_process_alive(pid, instance_id):
                return True
            time.sleep(0.2)
        return not self.is_process_alive(pid, instance_id)

    def _cleanup_run_files(self, instance_id: int) -> None:
        self._stop_path(instance_id).unlink(missing_ok=True)
        self._worker_path(instance_id).unlink(missing_ok=True)

    def read_logs(self, instance_id: int, max_bytes: int = 64 * 1024) -> tuple[str, bool]:
        path = self.log_path(instance_id)
        if not path.is_file():
            return "", False
        size = path.stat().st_size
        with open(path, "rb") as log_file:
            if size > max_bytes:
                log_file.seek(-max_bytes, os.SEEK_END)
            data = log_file.read()
        return data.decode("utf-8", errors="replace"), size > max_bytes

    def _last_log_line(self, instance_id: int) -> str:
        content, _ = self.read_logs(instance_id, max_bytes=4096)
        for line in reversed(content.splitlines()):
            cleaned = line.strip()
            if cleaned:
                return cleaned[:300]
        return ""

    def remove(self, instance_id: int) -> None:
        path = self.instance_dir(instance_id)
        if path.exists():
            shutil.rmtree(path)

    def stop_all(self) -> None:
        if not self.instances_dir.exists():
            return
        for child in self.instances_dir.iterdir():
            if not child.is_dir() or not child.name.isdigit():
                continue
            instance_id = int(child.name)
            info = self.read_worker_info(instance_id)
            pid = info.pid if info is not None else None
            if pid:
                self.stop(instance_id, pid, timeout=3.0)
