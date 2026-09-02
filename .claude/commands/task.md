---
description: Do a job against the Flow PT API, grounded in the corpus
---

Job: $ARGUMENTS

The corpus lives in the sibling repo `../fpt-llm-api`. This repo never probes; it consumes.

1. Read `../fpt-llm-api/corpus/INDEX.md`. Nothing else yet.
2. Open only the entries whose tags match this job.
3. List what the job needs that no entry covers. That is the gap.
4. A gap is not this repo's to fill. Say so and stop — the probe belongs in `fpt-llm-api`.
5. Otherwise do the job, citing entries in the code: `# probe 004`.

Publish path is REST and `requests` only, through `sg_groundtruth.client`. Never `shotgun_api3`, never `fpt-api`.
