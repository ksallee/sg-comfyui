---
description: Do a job against the Flow Production Tracking API, grounded in the corpus
---

Job: $ARGUMENTS

The corpus is in the `sg-groundtruth` checkout, `../sg-groundtruth` beside a repo checkout. A
Registry install has none, so clone it first: INSTALL.md, "Measuring a site without an agent", says
where. `<groundtruth>` below is that path. This pack does not probe.

1. Read `<groundtruth>/corpus/INDEX.md`. Nothing else yet.
2. Open only the entries whose tags match this job.
3. List what the job needs that no entry covers. That is the gap.
4. A gap is not this pack's to fill. Say so and stop. The probe belongs in `sg-groundtruth`.
5. Otherwise do the job, citing entries in the code: `# probe 004`.

Publish path is REST and `requests` only, through `sg_groundtruth.client`. Never `shotgun_api3`, never `fpt-api`.
