from pathlib import Path

from app.adapters.compute.process_adapter import ProcessComputeAdapter

APPLICATION_WORKER_SCRIPT = Path(__file__).resolve().with_name("application_worker.py")


class LocalAppRunner(ProcessComputeAdapter):
    """Run the controlled sample web application as a managed local process."""

    adapter_name = "process"

    def __init__(self, applications_dir: Path, port_start: int, port_end: int) -> None:
        super().__init__(
            applications_dir,
            port_start,
            port_end,
            worker_script=APPLICATION_WORKER_SCRIPT,
        )
