---
description: Do a job against the Flow PT API, grounded in probe findings
---

Job: $ARGUMENTS

1. Read `probes/findings/INDEX.md`. Nothing else yet.
2. Pick the findings whose tags match this job. Open only those.
3. List what the job needs that no finding covers. That list is the gap.
4. Probe the gap first — one probe per question, `/probe` conventions. Read-only unless the job needs writes.
5. Run `python probes/index.py`.
6. Then do the job, citing findings in the code: `# probe 004`.

Never code against `docs/quirks.md`. Those are unverified claims — if the job depends on one, it is a gap.

Publish path is REST and `requests` only. Setup path may use the Python API. See DESIGN.md.
