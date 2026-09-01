# Probes

The REST docs are incomplete and sometimes wrong. Every behaviour this repo relies on is proved here first.

    cp ../.env.local.example ../.env.local   # fill in
    python probes/001_auth.py

One question per probe. Read-only unless run with `--write`. Findings in `findings/` are the spec — sanitized, committed, and cited from the code.
