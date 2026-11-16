# Security Notes
- Local educational use only; not production-hardened
- Hash passwords with a suitable password-hashing library
- Keep secrets in environment variables; never commit `.env`
- Enforce ownership and authorization on every resource endpoint
- Validate filenames, sizes, SQL operations, ports, and deployment inputs
- Avoid arbitrary code execution and unrestricted shell commands
- Bind to localhost by default; do not expose to LAN or internet without security review
