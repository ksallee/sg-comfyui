# sg-comfyui

ComfyUI nodes that publish generations to Flow Production Tracking with provenance.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow Production Tracking REST docs and this repo's probe findings.

Out of scope, permanently: charts, dashboards, scheduled reports, webhooks, automations. Do not add them.

## The corpus lives next door

`../sg-groundtruth` holds every verified truth about the API, and the client. This repo probes nothing and
duplicates nothing.

Read `../sg-groundtruth/corpus/INDEX.md` first, always. Never code against behaviour no entry covers — that is a
gap, and the probe that closes it belongs in `sg-groundtruth`. Code cites entries: `# probe 004`.

Plan for both repos: `../sg-groundtruth/PLAN.md` — older, and stale where this repo has moved past it.

`RELEASE.md` is what is being built now, what was decided and why, and what is still open. Read it
before starting work.

## Stack

Python 3.11. `sg_groundtruth` for all site access, plus what ComfyUI already ships: `requests`, `Pillow`. Never
`shotgun_api3`, never `fpt-api` — it is AGPL. A new dependency needs a line in DESIGN.md justifying it.

`sg_groundtruth` is a normal PyPI dependency — install `requirements.txt` into the interpreter ComfyUI runs on.
The sibling checkout is still expected for the *corpus* and for `inspect_site.py`, which the package does not ship.

## Running it

Everything runs from the repo root. Every `-m comfyui_sg.*` needs `PYTHONPATH=src` — the package
lives under `src/` and nothing installs it. `instrument.py` is run as a file on purpose: `-m` would
import the package `__init__` and therefore torch, and a graph must stay analysable on a machine with
neither torch nor a route to the site.

Operation is `README.md`. The recurring jobs are slash commands: `/inspect-site` writes
`profile.local.json`, which is gitignored and which every picker reads; without it the pickers run
on the site's defaults, which carry a Shot-linked show. `/track-workflow` puts the nodes into a
graph the operator already uses. `tools/doctor.py` is the offline check, run as a file.

`tests/` runs with no site, no ComfyUI and no torch: `uv run --with pytest --with numpy --with Pillow
--with requests --with sg-groundtruth --python 3.11 python -m pytest -q`. CI runs it on three
platforms on every push.

## Secrets

Settings, then SG, in the editor: a person signs in through the App Session Launcher, or a script
name and key are entered there. Both land in ComfyUI's protected user directory, never in its
settings store, which anyone on the port can read. `.env.local`, gitignored, is the checkout and
farm path. Never printed or logged.

## ComfyUI

Node classes register through `NODE_CLASS_MAPPINGS` in `__init__.py`. `INPUT_TYPES` is a classmethod evaluated
at load — that is the hook the site mapping drives. Provenance comes from the hidden `PROMPT` and
`EXTRA_PNGINFO` inputs, never from asking the user.

Where each piece of provenance lands in Flow Production Tracking is the operator's mapping, not a default. See DESIGN.md.

**`widgets_values` is positional.** A widget inserted, removed or reordered displaces every value below it
in every graph already saved, silently — so append, never insert, and never remove. The order is declared
once, in `widgets.py`; `INPUT_TYPES`, `instrument.py` and the editor's `DECLARED` derive from it, and every
`*.json` under `example_workflows/` and `tools/workflows/` carries one value per declared widget, so a new
widget means a new value in every shipped graph in the same commit. `tests/test_widget_order.py` proves
the order and the fixtures offline; `tools/smoke.py` proves the round trip, because only loading a saved
graph in a real ComfyUI shows the shift. **An output is positional too**: a saved graph names a slot
by its index, so the order in `RETURN_NAMES` is frozen from the first release and appending is the
only safe change after it. An input *slot* is different: adding one is additive and safe.

**This node records; it does not make media.** Review media is derived and may be transcoded; a deliverable
file is never transformed. Nothing here has an encoder or a decoder of its own: frames are written by
ComfyUI's image encoder in the format the operator picked, clips by `VideoInput.save_to()`, and both are
read back by ComfyUI's decoder. Pillow writes the 8-bit review still and nothing else.

## Agent-operable

Forkers drive this repo with an agent, not by reading it. Small files, explicit names, no magic, no indirection. Conventions live here or in DESIGN.md — once, in one place.

## Messages to the operator

Every string a person reads — a node error, a panel line, an alert, a tooltip — has one shape.

- **Say what to do.** Name the fields or the action. Never describe the consequence of leaving a
  field empty. `Fill in the required fields (project, link).` — not `nothing is linked, so the name
  has no shot or asset in it`.
- **Wrong, then the fix**, in that order, one idea per sentence.
  `No Shot named sh010 on this project. Pick one from the list.`
- **Use the words on screen.** `Tick Create Published Files`, never `register_files`.
- **No internal vocabulary.** Not "single-valued", not "the truth table", not "a Version holds one
  piece of media". The operator does not have the docs open.
- Full sentences, sentence case, a full stop. No em-dash chains and no clause stacked on clause.
- **A tooltip** says what the widget sets, in one sentence, plus an example where the format is not
  obvious from the name.
- Diagnostic detail — a status code, a server body, a path — comes after the plain sentence, never
  instead of it.

## Style

Terse and declarative. The code says what it is; comments and docstrings do not narrate how it got
there.

- **Docstrings** are one short sentence saying what the thing does. A parameter gets a short phrase
  only where its name does not already say it. A function whose behaviour is genuinely not
  self-evident may take three or four more sentences — that is the exception, not the shape.
- **Comments** appear only where the code alone is hard to follow, and state the rule or the
  constraint, never its discovery.
- **No history.** No dates, no "used to", no past bugs, no PR or commit numbers, no session
  narrative, no first person. What changed is in git; what was decided is in DESIGN.md.
- **`probe NNN` and `recipe NNN` citations stay.** They point at the corpus, which is the only
  reason this repo may claim anything about the API.
- A measured fact the code cannot show survives as one declarative line. Losing the fact is the only
  thing worse than telling its story.
