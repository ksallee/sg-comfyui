# sg-comfyui

ComfyUI nodes that publish generations to Flow Production Tracking with provenance.

## Clean room

Never read `~/dev/fpt-ai`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Sources: the public Flow Production Tracking REST docs and the corpus in `../sg-groundtruth`.

Out of scope, permanently: charts, dashboards, scheduled reports, webhooks, automations.

## The corpus

`../sg-groundtruth/corpus/INDEX.md` lists every verified fact about the API and the client. Read it
before coding against the API. Code cites the entry it rests on: `# probe 004`.

Behaviour with no entry is a gap. The probe that closes it goes in `sg-groundtruth`, not here.

`RELEASE.md`: what is being built, what was decided, what is open. Read it before starting work.
`../sg-groundtruth/PLAN.md` is older and stale where this repo has moved past it.

## Stack

- Python 3.11.
- Site access: `sg_groundtruth`, from PyPI, installed by `requirements.txt` into the interpreter
  ComfyUI runs on.
- Also used: `requests`, `Pillow`, both shipped by ComfyUI.
- Never `shotgun_api3`. Never `fpt-api` (AGPL).
- A new dependency needs a line in DESIGN.md.
- The sibling checkout `../sg-groundtruth` is still needed for the corpus and for `inspect_site.py`.

## Process

- Branch from `dev`. Open a PR onto `dev`. Squash-merge it once the suite and the site build pass.
  Merging onto `dev` is authorized in the session.
- `main` is human-gated: Kevin QAs `dev` and promotes it by merge commit, unless he says otherwise
  in the session.

## Running it

- Run from the repo root.
- `python -m comfyui_sg.*` needs `PYTHONPATH=src`. Nothing installs the package.
- `instrument.py` runs as a file, not with `-m`. `-m` imports the package `__init__`, which imports torch.
- `/inspect-site` writes `profile.local.json` (gitignored). Every picker reads it. Without it the
  pickers use the site's defaults.
- `/track-workflow` adds the nodes to an existing graph.
- `tools/doctor.py` is the offline check. Run it as a file.
- Tests need no site, no ComfyUI, no torch:

```sh
uv run --with pytest --with numpy --with Pillow --with requests --with sg-groundtruth --python 3.11 python -m pytest -q
```

CI runs the tests on Linux, macOS and Windows on every push.

## Secrets

- In the editor: Settings, then SG. Sign in through the App Session Launcher, or enter a script name
  and key.
- Both are stored in ComfyUI's protected user directory. Never in the settings store, which anyone on
  the port can read.
- `.env.local` (gitignored) is the path for a checkout and a farm.
- Never print or log a secret.

## ComfyUI

- Node classes register through `NODE_CLASS_MAPPINGS` in `__init__.py`.
- `INPUT_TYPES` is a classmethod evaluated at load. The site mapping is applied there.
- Provenance comes from the hidden `PROMPT` and `EXTRA_PNGINFO` inputs. Never ask the user for it.
- Where each provenance field lands in Flow Production Tracking is the operator's mapping. See DESIGN.md.

**`widgets_values` is positional.** A widget inserted, removed or reordered shifts every value below
it in every saved graph, silently.

- Append. Never insert. Never remove.
- The order is declared once, in `widgets.py`. `INPUT_TYPES`, `instrument.py` and the editor's
  `DECLARED` read it from there.
- Every `*.json` under `example_workflows/` and `tools/workflows/` has one value per declared widget.
  A new widget means a new value in every shipped graph, in the same commit.
- `tests/test_widget_order.py` checks the order and the fixtures offline. `tools/smoke.py` loads
  each graph in a real ComfyUI.

**Outputs are positional.** A saved graph links a slot by index. The order in `RETURN_NAMES` is frozen
from the first release. Append only. Adding an input slot is safe.

**This node records. It does not make media.**

- Review media is derived and may be transcoded. A deliverable file is never transformed.
- Frames are written by ComfyUI's image encoder in the format the operator picked. Clips are written
  by `VideoInput.save_to()`. Both are read back by ComfyUI's decoder.
- Pillow writes the 8-bit review still. Nothing else.

## Agent-operable

Forkers work on this repo through an agent. Small files, explicit names, no magic, no indirection.
A convention is written once, here or in DESIGN.md.

## Messages to the operator

Applies to node errors, panel lines, alerts, tooltips.

- **Say what to do.** Name the field or the action. `Fill in the required fields (project, link).`
  Not `nothing is linked, so the name has no shot or asset in it`.
- **Wrong, then the fix.** `No Shot named sh010 on this project. Pick one from the list.`
- **Use the words on screen.** `Tick Create Published Files`. Never `register_files`.
- **No internal vocabulary.** Not "single-valued", not "the truth table". The operator does not have
  the docs open.
- Full sentences. Sentence case. A full stop. One idea per sentence.
- **A tooltip** says what the widget sets, in one sentence, plus an example where the format is not
  obvious from the name.
- Diagnostic detail (status code, server body, path) comes after the plain sentence. Never instead
  of it.

## Writing

Every document, docstring, comment, drive header, commit message and report is reference material.
The reader scans it.

- One fact, once, in the plainest words. Never restate a fact in other words.
- One fact per sentence. Nothing appended to justify it. The why is in DESIGN.md.
- Imperative for a step. `Restart ComfyUI.`
- Name, then value. `Requires ComfyUI 0.34.0.`
- A list or a table before a paragraph. A paragraph is three sentences at most.
- A command is a fenced block under a heading, with at most one line saying when to run it.
- A claim is short and exact. `A Version has one uploaded media file.`
- A measured fact the code cannot show is one declarative line with its `probe NNN` or
  `recipe NNN` citation. The citations stay.

Banned:

- Em dashes and en dashes. Use a full stop or a comma.
- Metaphor and personification: `drives`, `lives`, `hangs off`, `the panel says`, `the site answers`,
  `earns its place`, `keeps true`.
- Emphasis words: `every`, `always`, `never` used for effect, `whole`, `real`, `true`, `proper`,
  `genuinely`, `exactly`, `the single way`, `the one command`, `and nothing else`, `once, in one place`.
- Hedges: `roughly`, `generally`, `usually`, `tends to`, `more or less`, `in practice`, `essentially`.
- Vague verbs: `carry`, `hold`, `live`, `land`, `sit`. Say the relation: has, records, lists, links to,
  is set to, points at, is stored in.
- Rhetorical setup: `in other words`, `which is why`, `that is the hook`, `the reader scans it, nobody
  reads it through`, aphorisms, a sentence that exists to introduce the next one.
- Selling: `no studio's conventions are hardcoded`, `the pack's whole proposition`.
- History: dates, `used to`, past bugs, PR and commit numbers, session narrative, first person.

Docstrings: one sentence saying what the thing does. A parameter gets a phrase only where its name
does not say it. Up to four more sentences where the behaviour is not evident from the code.

Comments: only where the code is hard to follow. State the rule or the constraint, not its discovery.
