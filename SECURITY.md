# Security Note

An Africa's Talking API key was committed to this repository's git history. Because git history preserves old file contents even after a file is untracked, that key must be treated as compromised and **rotated in the Africa's Talking dashboard** (revoke the exposed key and generate a new one). This is a manual action for the project owner; the new key belongs only in your local `.env`, which is no longer tracked by git.
