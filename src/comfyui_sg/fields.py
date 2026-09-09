"""Typed provenance fields on Version: the list, the idempotent create, and where each concept lands.

Setup path for `ensure` — run once per site by the operator (`python -m comfyui_sg.fields`); the
node only reads the result. The routing half (`concepts`, `targets`, `route`) runs on the publish
path and consults nothing but its arguments.

Field names are permanent. probe 019 — DELETE frees the field but never its name, and trashed fields
cannot be enumerated, so a name spent here is spent site-wide forever. Add to FIELDS deliberately.

Display and programmatic names are kept in step: the site derives one from the other at creation, and
a TD reading `sg_ai_generated_from` in the schema must find "AI Generated From" in the UI. Relabelling
alone breaks that correspondence, so a rename means a new field.
"""
import re

# (display name, data_type, extra properties). Chosen to fit any graph, not one workflow: every
# diffusion sampler has a seed, steps and cfg; every graph loads a model; text prompts may be absent
# (img2img, video) and simply stay empty.
FIELDS = [
    ("AI Generator",       "text",         {}),
    ("AI Model",           "text",         {}),
    ("AI Prompt",          "text",         {}),
    ("AI Negative Prompt", "text",         {}),
    # probe 019 — a number field takes 2**31-1 but 400s at 2**63, and ComfyUI seeds reach 2**64-1.
    ("AI Seed",            "text",         {}),
    ("AI Sampler",         "text",         {}),
    ("AI Steps",           "number",       {}),
    ("AI CFG",             "float",        {}),
    # probe 019 — valid_types takes exactly one element; two returns 400.
    # "Generated From", not "Source Versions": the sources need not be AI — a scanned plate feeding a
    # previs is the ordinary case. The AI describes THIS Version's generation, not its inputs.
    ("AI Generated From",  "multi_entity", {"valid_types": ["Version"]}),
]


def programmatic_name(display):
    """probe 019 — the site lowercases the display name, replaces each non-alphanumeric character
    with an underscore, and prefixes sg_. Takes a display name: 'sg_x' would become 'sg_sg_x'."""
    return "sg_" + re.sub(r"[^a-z0-9]", "_", display.lower())


def names():
    """{display name: programmatic name} for every field in FIELDS."""
    return {display: programmatic_name(display) for display, _, _ in FIELDS}


class Refused(RuntimeError):
    """The site would not answer. `status` is what it answered, for a caller that says who can."""

    def __init__(self, sentence, status):
        super().__init__(sentence)
        self.status = status


def _schema(sg, entity_type):
    """Every field on the type. probe 002 — the expensive call, so it is made once per run."""
    r = sg.get(f"/schema/{entity_type}/fields")
    if not r.ok:
        raise Refused(f"Could not read the {entity_type} fields from Flow Production Tracking. "
                      f"Check that the script key is allowed to read the schema, then run again. "
                      f"The site answered {r.status_code}. {r.text[:200]}", r.status_code)
    return r.json()["data"]


def survey(sg, entity_type="Version"):
    """{present, missing, total} by display and programmatic name, from one schema read."""
    existing = _schema(sg, entity_type)
    rows = [{"display": d, "name": n} for d, n in names().items()]
    return {"present": [f for f in rows if f["name"] in existing],
            "missing": [f for f in rows if f["name"] not in existing],
            "total": len(FIELDS)}


def ensure(sg, entity_type="Version"):
    """Create whatever is missing. Returns (present, created, failed) for the caller to report.

    probe 019 — reading /schema first is mandatory, not an optimisation: POSTing a display name that
    already exists does NOT error, it silently creates <name>_1 and every later run adds another.
    """
    existing = _schema(sg, entity_type)

    present, created, failed = [], [], []
    for display, data_type, extra in FIELDS:
        name = programmatic_name(display)
        if name in existing:
            present.append((display, name, existing[name].get("data_type", {}).get("value")))
            continue
        props = [{"property_name": "name", "value": display}]
        props += [{"property_name": k, "value": v} for k, v in extra.items()]
        resp = sg.post(f"/schema/{entity_type}/fields",
                        json={"data_type": data_type, "properties": props})
        if resp.ok:
            created.append((display, resp.json().get("links", {}).get("self", "").rsplit("/", 1)[-1]))
        else:
            failed.append((display, name, data_type, _explain(resp)))
    return present, created, failed


def _explain(resp):
    """Turn an API error into something an operator can act on."""
    try:
        err = resp.json()["errors"][0]
        title = err.get("title", "")
        source = err.get("source") or ""
    except Exception:
        return f"The site answered {resp.status_code}. {resp.text[:160]}"

    if "schema_field_create() failed" in title:
        return (f"The name is almost certainly held by a field in the trash. Rename this field in "
                f"fields.py, changing its display name, then run again. Deleting a field never "
                f"frees its name and trashed fields cannot be listed, so the clash is invisible "
                f"(probe 019). The site said {title}")
    if "Only true or false" in title:
        return f"A checkbox needs a default_value property. Add one in fields.py, then run again. "\
               f"The site said {title}"
    if "missing required 'properties'" in title:
        return f"An entity or multi_entity field needs valid_types with exactly one type in it. "\
               f"Add it in fields.py, then run again. The site said {title}"
    if "data_type is not valid" in str(source):
        return f"This data type cannot be created over the API, so add the field in the "\
               f"Flow Production Tracking web UI instead (probe 019). The site said {title} {source}"
    return f"The site answered {resp.status_code}. {title} {source}".strip()


def report(present, created, failed):
    """What `ensure` did, one line per field."""
    lines = []
    for display, name, dt in present:
        lines.append(f"  ok       {display:<20} {name:<28} ({dt})")
    for display, name in created:
        lines.append(f"  CREATED  {display:<20} {name}")
    for display, name, dt, why in failed:
        lines.append(f"  FAILED   {display:<20} {name:<28} [{dt}]\n           {why}")
    if not failed:
        lines.append(f"\n{len(present)} already present, {len(created)} created, 0 failed.")
    else:
        lines.append(f"\n{len(present)} present, {len(created)} created, {len(failed)} failed. "
                     f"The facts those fields would hold go into the attached JSON file instead.")
    return "\n".join(lines)


def outcome(present, created, failed):
    """`ensure`'s three buckets as one row per field: {display, name, state, why}."""
    rows = [{"display": d, "name": n, "state": "ok"} for d, n, _ in present]
    rows += [{"display": d, "name": programmatic_name(d), "state": "created"} for d, _ in created]
    rows += [{"display": d, "name": n, "state": "failed", "why": why} for d, n, _, why in failed]
    return rows


def schema_names(sg, entity_type="Version"):
    """Every field this site has on the type. probe 002 — the expensive call, so one per publish.

    Unreadable schema is an empty set, which reads as "write nothing optional": a publish that cannot
    see the schema must not guess a field into a 400.
    """
    r = sg.get(f"/schema/{entity_type}/fields")
    return set(r.json()["data"]) if r.ok else set()


def available(sg, entity_type="Version"):
    """Which provenance fields actually exist on this site right now."""
    return set(names().values()) & schema_names(sg, entity_type)


# What the graph knows, named as concepts rather than as fields. The operator decides where each one
# lands (site.provenance_map); DEFAULT_MAP is only what happens when they have not said.
DEFAULT_MAP = {
    "generator":       "sg_ai_generator",
    "model":           "sg_ai_model",
    "prompt":          "sg_ai_prompt",
    "negative_prompt": "sg_ai_negative_prompt",
    "seed":            "sg_ai_seed",
    "sampler":         "sg_ai_sampler",
    "steps":           "sg_ai_steps",
    "cfg":             "sg_ai_cfg",
    "generated_from":  "sg_ai_generated_from",
}
DESCRIPTION = "description"
CONCEPT_LABELS = {"generator": "made by", "model": "model", "prompt": "prompt",
                  "negative_prompt": "negative prompt", "seed": "seed", "sampler": "sampler",
                  "steps": "steps", "cfg": "cfg", "generated_from": "generated from"}


def targets(mapping=None, mode="fields"):
    """{concept: target} — the operator's decision, resolved once and read by everyone.

    Target is a Version field, DESCRIPTION, or None for "do not record this". Shared with
    /sg/preview_publish so the panel shows where a value will actually land, not where this file
    would have put it.
    """
    mapping = mapping or {}
    fallback = DESCRIPTION if mode == DESCRIPTION else None
    return {c: mapping.get(c, DEFAULT_MAP[c] if fallback is None else fallback) for c in DEFAULT_MAP}


def route(prov, source_version_ids=(), mapping=None, mode="fields"):
    """({field: value}, [readable line]) — where each concept the graph knows actually lands.

    `mapping` is the operator's, from the profile: concept -> a Version field, DESCRIPTION, or None
    to record it nowhere. A concept they did not name follows `mode`, which is the whole point of
    having a mode: "put everything in the description" is one word, not nine null entries.

    Nothing here consults the site. A target that does not exist is the caller's to report, because
    silently dropping a field the operator explicitly asked for is the failure worth being loud about.
    """
    where = targets(mapping, mode)
    fields, lines = {}, []
    for concept, value in concepts(prov, source_version_ids).items():
        target = where.get(concept)
        if not target:
            continue
        if target == DESCRIPTION:
            lines.append(f"{CONCEPT_LABELS.get(concept, concept)}: {_readable(concept, value)}")
        else:
            fields[target] = value
    return fields, lines


def _readable(concept, value):
    """A concept as one line of prose. Only `generated_from` is not already a scalar."""
    if concept == "generated_from":
        return ", ".join(f'Version {v["id"]}' for v in value)
    return str(value)


def concepts(prov, source_version_ids=()):
    """Provenance -> {concept: value}, before anything decides where it goes.

    Numeric fields take the LAST sampler: in a multi-sampler graph that is the one that produced the
    image being published. Text fields join every sampler, so nothing is lost. The full structure is
    attached as JSON regardless — these fields are the queryable summary, not the record of truth.

    Prompt comes from `prov["prompts"]`, not from the samplers, because half of these graphs never
    sample: "the actor" told a segmentation graph what to cut and is the same concept as "what to
    generate" — the words the artist gave the model. One field, one query. See DESIGN.md.
    """
    samplers = prov.get("samplers") or []
    last = samplers[-1] if samplers else {}
    prompts = prov.get("prompts") or {}

    def join(key):
        seen = []
        for s in samplers:
            v = s.get(key)
            for item in (v if isinstance(v, list) else [v]):
                if item not in (None, "") and item not in seen:
                    seen.append(item)
        return " | ".join(str(x) for x in seen)

    scheduler = join("scheduler")
    client = prov.get("comfy_usage_source") or "unknown client"
    out = {
        "generator": f"{prov.get('generator', 'ComfyUI')} ({client})",
        "model": " | ".join(dict.fromkeys(m["name"] for m in prov.get("models", []))),
        "prompt": " | ".join(prompts.get("positive") or []),
        "negative_prompt": " | ".join(prompts.get("negative") or []),
        "seed": join("seed"),                # text: 2**64 seeds overflow a number field (probe 019)
        "sampler": join("sampler_name") + (f"/{scheduler}" if scheduler else ""),
        "steps": last.get("steps"),
        "cfg": last.get("cfg"),
        # probe 019 — multi_entity round-trips {type, id} hashes and reads back under relationships.
        "generated_from": [{"type": "Version", "id": int(i)} for i in source_version_ids],
    }
    return {k: v for k, v in out.items() if v not in (None, "", [])}


if __name__ == "__main__":
    from . import site
    p, c, f = ensure(site.client())
    print(report(p, c, f))
    raise SystemExit(1 if f else 0)
