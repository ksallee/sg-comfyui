"""Typed provenance fields on Version, and the idempotent create that puts them there.

Setup path. Run once per site by the operator; the node only reads the result.

Field names are permanent. probe 019 — DELETE frees the field but never the name, and trashed fields
cannot be enumerated, so a name spent here is spent forever. Add to this list deliberately.

Display and programmatic names are kept in step on purpose: the site derives one from the other at
creation, and a TD reading `sg_ai_generated_from` in the schema should find "AI Generated From" in the
UI. Renaming only the label would break that correspondence for everyone who comes later.
"""
import re

DISPLAY_PREFIX = "AI"

# (display name, data_type, extra properties). Chosen to fit any graph, not one workflow:
# every diffusion sampler has a seed, steps and cfg; every graph loads a model; text prompts may be
# absent (img2img, video) and simply stay empty.
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
    # previs is the ordinary case. The AI modifies THIS Version's generation, not its inputs.
    ("AI Generated From",  "multi_entity", {"valid_types": ["Version"]}),
]


def programmatic_name(display):
    """probe 019 — the site lowercases the display name and replaces each non-alphanumeric character
    with an underscore, then prefixes sg_. Pass a display name: 'sg_x' would become 'sg_sg_x'."""
    return "sg_" + re.sub(r"[^a-z0-9]", "_", display.lower())


def names():
    return {display: programmatic_name(display) for display, _, _ in FIELDS}


def ensure(fpt, entity_type="Version"):
    """Create whatever is missing. Returns (present, created, failed) for the caller to report.

    probe 019 — reading /schema first is mandatory, not an optimisation: POSTing a display name that
    already exists does NOT error, it silently creates <name>_1 and every later run adds another.
    """
    r = fpt.get(f"/schema/{entity_type}/fields")
    if not r.ok:
        raise RuntimeError(f"cannot read {entity_type} schema: {r.status_code} {r.text[:200]}")
    existing = r.json()["data"]

    present, created, failed = [], [], []
    for display, data_type, extra in FIELDS:
        name = programmatic_name(display)
        if name in existing:
            present.append((display, name, existing[name].get("data_type", {}).get("value")))
            continue
        props = [{"property_name": "name", "value": display}]
        props += [{"property_name": k, "value": v} for k, v in extra.items()]
        resp = fpt.post(f"/schema/{entity_type}/fields",
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
        return f"HTTP {resp.status_code}: {resp.text[:160]}"

    if "schema_field_create() failed" in title:
        return (f"{title} — the name is almost certainly held by a TRASHED field. probe 019: deleting a "
                f"field never frees its name and trashed fields cannot be listed, so this collision is "
                f"invisible. Rename the field in fields.py (its display name) and re-run.")
    if "Only true or false" in title:
        return f"{title} — a checkbox needs a default_value property."
    if "missing required 'properties'" in title:
        return f"{title} — entity and multi_entity need valid_types (exactly one element)."
    if "data_type is not valid" in str(source):
        return f"{title} {source} — this data_type cannot be created over REST (probe 019)."
    return f"HTTP {resp.status_code}: {title} {source}".strip()


def report(present, created, failed):
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
        lines.append(f"\n{len(present)} present, {len(created)} created, {len(failed)} FAILED — "
                     f"the node will fall back to the JSON blob for those.")
    return "\n".join(lines)


if __name__ == "__main__":
    from . import site
    p, c, f = ensure(site.client())
    print(report(p, c, f))
    raise SystemExit(1 if f else 0)


def available(fpt, entity_type="Version"):
    """Which provenance fields actually exist on this site right now."""
    r = fpt.get(f"/schema/{entity_type}/fields")
    if not r.ok:
        return set()
    schema = r.json()["data"]
    return {n for n in names().values() if n in schema}


def values_for(prov, source_version_ids=()):
    """Provenance -> {programmatic_name: value}, for every field this module defines.

    Numeric fields take the LAST sampler: in a multi-sampler graph that is the one that produced the
    image being published. Text fields join every sampler, so nothing is lost. The full structure is
    attached as JSON regardless — these fields are the queryable summary, not the record of truth.
    """
    samplers = prov.get("samplers") or []
    last = samplers[-1] if samplers else {}

    def join(key):
        seen = []
        for s in samplers:
            v = s.get(key)
            for item in (v if isinstance(v, list) else [v]):
                if item not in (None, "") and item not in seen:
                    seen.append(item)
        return " | ".join(str(x) for x in seen)

    client = prov.get("comfy_usage_source") or "unknown client"
    out = {
        "sg_ai_generator": f"{prov.get('generator', 'ComfyUI')} ({client})",
        "sg_ai_model": " | ".join(dict.fromkeys(m["name"] for m in prov.get("models", []))),
        "sg_ai_prompt": join("positive"),
        "sg_ai_negative_prompt": join("negative"),
        "sg_ai_seed": join("seed"),          # text: 2**64 seeds overflow a number field (probe 019)
        "sg_ai_sampler": join("sampler_name") + ("/" + join("scheduler") if join("scheduler") else ""),
        "sg_ai_steps": last.get("steps"),
        "sg_ai_cfg": last.get("cfg"),
        # probe 019 — multi_entity round-trips {type, id} hashes and reads back under relationships.
        "sg_ai_generated_from": [{"type": "Version", "id": int(i)} for i in source_version_ids],
    }
    return {k: v for k, v in out.items() if v not in (None, "", [])}
