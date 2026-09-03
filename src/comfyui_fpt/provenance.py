"""Provenance extracted from the executing ComfyUI graph.

PROMPT is the API-format graph: {node_id: {"class_type", "inputs", "_meta"}}. Values in `inputs` are
either widget values or links of the form [node_id, output_slot].

PROMPT is always present — execution requires it. EXTRA_PNGINFO is whatever the client put in
extra_data and is None otherwise (execution.py:199), so any API, CLI or MCP client yields no workflow.
Treat the workflow as best effort; never make a publish depend on it.
"""

SEED_KEYS = ("seed", "noise_seed")
SAMPLER_KEYS = ("steps", "cfg", "sampler_name", "scheduler", "denoise", "start_at_step", "end_at_step")
# `model_name` is the generic one: depth estimators, upscalers and most auxiliary loaders use it.
MODEL_KEYS = ("ckpt_name", "unet_name", "vae_name", "clip_name", "control_net_name",
              "style_model_name", "model_name")
LORA_KEYS = ("lora_name", "strength_model", "strength_clip")


def _is_link(v):
    return isinstance(v, list) and len(v) == 2 and isinstance(v[1], int)


def _widgets(node):
    return {k: v for k, v in (node.get("inputs") or {}).items() if not _is_link(v)}


def _order(prompt):
    # Node ids are strings but numeric in practice; fall back to string order for expanded nodes.
    def key(nid):
        return (0, int(nid)) if str(nid).isdigit() else (1, str(nid))
    return sorted(prompt, key=key)


def _trace_text(prompt, ref, role=None, seen=None):
    """Walk a conditioning link back to the text behind it.

    Conditioning reaches a sampler through ControlNet, combine and guidance nodes, so the encoder is
    rarely one hop away. Returns every distinct text found upstream, nearest first.

    `role` is the sampler input we started from. It matters because nodes like ControlNetApplyAdvanced
    take BOTH positive and negative: following every link from there merges the two prompts into one,
    so when a node has an input matching the role, that is the only branch worth taking.
    """
    seen = seen if seen is not None else set()
    if not _is_link(ref):
        return []
    nid = str(ref[0])
    if nid in seen or nid not in prompt:
        return []
    seen.add(nid)
    node = prompt[nid]
    found = [v for k, v in _widgets(node).items() if k == "text" and isinstance(v, str)]
    links = [(k, v) for k, v in (node.get("inputs") or {}).items() if _is_link(v)]
    if role and any(k == role for k, _ in links):
        links = [(k, v) for k, v in links if k == role]
    for _, v in links:
        found += _trace_text(prompt, v, role, seen)
    out = []
    for t in found:
        if t not in out:
            out.append(t)
    return out


def ancestors(prompt, node_id):
    """Every node upstream of node_id.

    One graph often holds several independent branches — three lookdev variants off a shared depth
    pass — and each publish node must describe the branch that produced ITS image, not the whole file.
    Without this every Version carries every other variant's prompt and seed.
    """
    seen, stack = set(), [str(node_id)]
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in prompt:
            continue
        seen.add(nid)
        for v in (prompt[nid].get("inputs") or {}).values():
            if _is_link(v):
                stack.append(str(v[0]))
    return seen


def loaded_versions(prompt, node_id):
    """Version ids pulled from Flow PT upstream of node_id, in graph order.

    Lineage the operator never types. Only a PINNED id is in the prompt; a Load node resolving by
    rule knows its Version at run time, and records it in `lineage` instead. Both are read.

    `version_id` is the old spelling, kept so a graph saved before the Load node was reworked still
    reports its lineage rather than silently losing it.
    """
    ids, scope = [], ancestors(prompt, node_id)
    for nid in _order(prompt):
        if nid not in scope:
            continue
        node = prompt.get(nid) or {}
        if node.get("class_type") != "FPTLoadVersion":
            continue
        inputs = node.get("inputs") or {}
        vid = inputs.get("pin_version_id", inputs.get("version_id"))
        if isinstance(vid, int) and vid > 0 and vid not in ids:
            ids.append(vid)
    return ids


def extract(prompt, extra_pnginfo=None, node_id=None):
    """Everything the graph knows about how this image was made.

    node_id is the publishing node's UNIQUE_ID; given it, only that node's branch is described.
    """
    prompt = prompt or {}
    scope = (ancestors(prompt, node_id)
             if node_id is not None and str(node_id) in prompt else set(prompt))
    models, loras, samplers = [], [], []

    for nid in _order(prompt):
        if nid not in scope:
            continue
        node = prompt[nid] or {}
        cls = node.get("class_type")
        w = _widgets(node)

        for k in MODEL_KEYS:
            if k in w:
                models.append({"node_id": nid, "class_type": cls, "role": k, "name": w[k]})
        if "lora_name" in w:
            loras.append({"node_id": nid, "name": w["lora_name"],
                          **{k: w[k] for k in LORA_KEYS if k in w and k != "lora_name"}})

        seed = next((w[k] for k in SEED_KEYS if k in w), None)
        if seed is not None:
            s = {"node_id": nid, "class_type": cls, "seed": seed}
            s.update({k: w[k] for k in SAMPLER_KEYS if k in w})
            links = node.get("inputs") or {}
            s["positive"] = _trace_text(prompt, links.get("positive"), "positive")
            s["negative"] = _trace_text(prompt, links.get("negative"), "negative")
            samplers.append(s)

    return {
        "generator": "ComfyUI",
        "models": models,
        "loras": loras,
        "samplers": samplers,
        "node_count": len(scope),
        "workflow_attached": workflow(extra_pnginfo) is not None,
    }


def workflow(extra_pnginfo):
    """The editor graph, for attaching as a file. None unless the client sent it (execution.py:199)."""
    if not isinstance(extra_pnginfo, dict):
        return None
    return extra_pnginfo.get("workflow")
