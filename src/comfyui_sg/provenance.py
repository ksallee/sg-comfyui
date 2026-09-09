"""Provenance read out of the executing ComfyUI graph.

PROMPT is the API-format graph: {node_id: {"class_type", "inputs", "_meta"}}. A value in `inputs` is
either a widget value or a link of the form [node_id, output_slot].

PROMPT is always present — execution requires it. EXTRA_PNGINFO is whatever the client put in
extra_data and is None otherwise (execution.py:199), so an API, CLI or MCP client yields no
workflow. The workflow is best effort; a publish never depends on it.
"""

SEED_KEYS = ("seed", "noise_seed")
SAMPLER_KEYS = ("steps", "cfg", "sampler_name", "scheduler", "denoise", "start_at_step", "end_at_step")
# `model_name` is the generic one: depth estimators, upscalers and most auxiliary loaders use it.
MODEL_KEYS = ("ckpt_name", "unet_name", "vae_name", "clip_name", "control_net_name",
              "style_model_name", "model_name")
LORA_KEYS = ("lora_name", "strength_model", "strength_clip")
# Words a node takes directly rather than through an encoder: every cloud generator (Kling, Veo,
# Runway, Qwen edit) and the edit encoders. Across core ComfyUI a STRING input named `prompt` is
# multiline on all 147 classes that declare one and never names a file, so the name alone is enough
# where reading every string widget would not be.
PROMPT_WIDGET_KEYS = {"prompt": "positive", "negative_prompt": "negative"}
# Text a CLIP encoder takes: `text` on one-encoder nodes, the rest on the per-tokeniser inputs of
# the dual and triple encoders — SDXL, Flux, SD3, HiDream, HunyuanDiT, Kandinsky5, Lumina2. Across
# all 908 core classes each name but `text` appears on exactly one class, always a multiline STRING
# on a node returning CONDITIONING, so the name alone identifies it.
#
# Deliberately absent: `tracks` (WanTrackToVideo — a JSON motion path, the `positive_coords` case
# again), `texts` (MakeTrainingDataset — a file list) and `tags`/`lyrics`/`caption` (the AceStep and
# MiniMax music encoders — an audio graph publishes no image, and a lyric sheet is a document rather
# than a direction).
ENCODER_TEXT_KEYS = ("text", "text_g", "text_l", "clip_l", "clip_g", "t5xxl", "llama",
                     "qwen25_7b", "bert", "mt5xl", "user_prompt")


def _is_link(v):
    return isinstance(v, list) and len(v) == 2 and isinstance(v[1], int)


def _widgets(node):
    return {k: v for k, v in (node.get("inputs") or {}).items() if not _is_link(v)}


def _order(prompt):
    # Node ids are strings but numeric in practice; expanded nodes fall back to string order.
    def key(nid):
        return (0, int(nid)) if str(nid).isdigit() else (1, str(nid))
    return sorted(prompt, key=key)


def _trace_text(prompt, ref, role=None, seen=None):
    """Every distinct text upstream of a conditioning link, nearest first.

    Conditioning reaches its consumer through ControlNet, combine and guidance nodes, so the encoder
    is rarely one hop away. `role` is the input the walk started from: a node such as
    `ControlNetApplyAdvanced` takes both positive and negative, so where a node has an input matching
    the role that is the only branch followed — otherwise the two prompts merge into one.
    """
    seen = seen if seen is not None else set()
    if not _is_link(ref):
        return []
    nid = str(ref[0])
    if nid in seen or nid not in prompt:
        return []
    seen.add(nid)
    node = prompt[nid]
    # ConditioningZeroOut erases what it is handed, so text behind it reached nothing. A Flux or SD3
    # negative is conventionally the positive encoder zeroed out, and this wall is what keeps such a
    # graph from reporting its positive prompt as its negative one too.
    if node.get("class_type") == "ConditioningZeroOut":
        return []
    # One node, several tokenisers: SDXL takes text_g and text_l, Flux clip_l and t5xxl. Identical
    # texts dedupe to one; texts that differ are kept separately, because concatenating would report
    # a sentence nobody typed and picking one would lose the other. `fields.concepts` joins the list
    # with " | " like any other.
    found = [v for k, v in _widgets(node).items() if k in ENCODER_TEXT_KEYS and isinstance(v, str)]
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


def _cond_role(key):
    """The role a conditioning input names — positive, negative or unroled; "" if it is not one.

    Prefix and not equality: `PairConditioningSetProperties` takes `positive_NEW`,
    `ConditioningCombine` takes `conditioning_1`, `DualCFGGuider` takes `cond1`. `SAM3_Detect`'s
    `positive_coords` is a JSON list of click points rather than conditioning, and is the one core
    input the prefix would otherwise catch.
    """
    if key.endswith("_coords"):
        return ""
    if key.startswith("positive"):
        return "positive"
    if key.startswith("negative"):
        return "negative"
    return "unroled" if key.startswith("cond") else ""


def directing_text(prompt, scope):
    """(positive, negative) — the words that told this branch what to do.

    Text becomes a prompt when an encoder turns it into CONDITIONING and a node consumes it. That
    holds for a sampler and equally for `SAM3_Detect`, whose `conditioning` input decides what gets
    cut out; a seed is not what makes text a prompt, and a segmentation graph has no seed at all.
    The consumption test is also the whole of the conservatism — `filename_prefix`, `ckpt_name` and
    a format enum are strings in the same graph and none of them reaches a conditioning input.

    `positive`/`negative` name a role, a bare `conditioning` input does not, and text found with no
    role reads as positive unless a roled walk already claimed it.
    """
    pos, neg, unroled = [], [], []
    bucket = {"positive": pos, "negative": neg, "unroled": unroled}
    for nid in _order(prompt):
        if nid not in scope:
            continue
        node = prompt[nid] or {}
        for k, v in (node.get("inputs") or {}).items():
            role = _cond_role(k) if _is_link(v) else ""
            if role:
                bucket[role] += _trace_text(prompt, v, None if role == "unroled" else role)
        for k, w in _widgets(node).items():
            if k in PROMPT_WIDGET_KEYS and isinstance(w, str) and w.strip():
                bucket[PROMPT_WIDGET_KEYS[k]].append(w)

    for t in unroled:
        if t not in pos and t not in neg:
            pos.append(t)
    return _said(pos), _said(neg)


def _said(texts):
    """Distinct non-empty texts, in the order found. An empty encoder said nothing."""
    out = []
    for t in texts:
        if t.strip() and t not in out:
            out.append(t)
    return out


def ancestors(prompt, node_id):
    """Every node upstream of node_id.

    One graph holds several independent branches — three lookdev variants off a shared depth pass —
    and each publish node describes the branch that produced ITS image, not the whole file.
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
    """Version ids pulled from SG upstream of node_id, in graph order.

    Only a PINNED id is in the prompt; a Load node resolving by rule records its Version in
    `lineage` instead, and both are read. `version_id` is an older spelling of the same widget and
    is still accepted.
    """
    ids, scope = [], ancestors(prompt, node_id)
    for nid in _order(prompt):
        if nid not in scope:
            continue
        node = prompt.get(nid) or {}
        if node.get("class_type") != "SGLoadVersion":
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

    positive, negative = directing_text(prompt, scope)

    return {
        "generator": "ComfyUI",
        "models": models,
        "loras": loras,
        "samplers": samplers,
        # The branch's prompt. `samplers` keeps its own copy because which text went into WHICH
        # sampler is a different fact, and a graph with no sampler still has this one.
        "prompts": {"positive": positive, "negative": negative},
        "node_count": len(scope),
        "workflow_attached": workflow(extra_pnginfo) is not None,
    }


def workflow(extra_pnginfo):
    """The editor graph, for attaching as a file. None unless the client sent it (execution.py:199)."""
    if not isinstance(extra_pnginfo, dict):
        return None
    return extra_pnginfo.get("workflow")
