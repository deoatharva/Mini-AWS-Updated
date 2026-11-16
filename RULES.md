# Development Rules
1. Implement in small, testable increments.
2. Read the PRD and architecture before coding.
3. Never fabricate resource status or test results.
4. Never store plaintext passwords or secrets.
5. Validate all inputs and enforce ownership checks.
6. Keep local services bound to localhost by default.
7. Never run arbitrary uploaded code or shell commands; use controlled templates and allowlisted operations.
8. Prevent path traversal and unsafe archive extraction.
9. Keep dependencies minimal and compatible with Windows.
10. Update the tracker and tests after each task.
