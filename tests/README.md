# Tests

Each backend test receives an isolated SQLite metadata database under a pytest
temporary directory, so tests never read or modify `data/mini_aws.db`.

Run backend tests from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -q .\tests\backend
```

Or run the full check (backend tests plus frontend production build):

```powershell
.\scripts\run_tests.ps1
```

Tests must verify real local effects. A mocked success path is not enough for a
resource operation to count as complete.
