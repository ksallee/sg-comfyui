"""API-format PROMPT graphs, hand-written: {node_id: {class_type, inputs}}.

A value in `inputs` is either a widget value or a link, `[node_id, output_slot]`. The shapes
provenance has to read correctly: a zeroed-out negative, two tokenisers on one encoder, two branches
off one node, a node taking words as a widget, and roles that must not merge.
"""

PUBLISH = "SGPublishVersion"
LOAD = "SGLoadVersion"


def sdxl_zero_out():
    """SDXL, one encoder with two tokenisers, the negative zeroed out."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "2": {"class_type": "CLIPTextEncodeSDXL",
              "inputs": {"text_g": "a red car", "text_l": "studio light", "clip": ["1", 1]}},
        "3": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["2", 0]}},
        "4": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "5": {"class_type": "KSampler",
              "inputs": {"seed": 42, "steps": 20, "cfg": 7.5, "sampler_name": "euler",
                         "scheduler": "normal", "denoise": 1.0, "model": ["1", 0],
                         "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": PUBLISH, "inputs": {"images": ["6", 0]}},
    }


def flux_dual_encoder():
    """Flux: one encoder, two tokenisers holding different text, and a LoRA on the model."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors"}},
        "2": {"class_type": "DualCLIPLoader",
              "inputs": {"clip_name1": "t5xxl_fp16.safetensors",
                         "clip_name2": "clip_l.safetensors"}},
        "3": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"lora_name": "film_grain.safetensors", "strength_model": 0.6,
                         "model": ["1", 0]}},
        "4": {"class_type": "CLIPTextEncodeFlux",
              "inputs": {"clip_l": "a lighthouse", "t5xxl": "a lighthouse in a storm at dusk",
                         "guidance": 3.5, "clip": ["2", 0]}},
        "5": {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6": {"class_type": "KSampler",
              "inputs": {"seed": 7, "steps": 28, "cfg": 1.0, "sampler_name": "dpmpp_2m",
                         "scheduler": "sgm_uniform", "denoise": 1.0, "model": ["3", 0],
                         "positive": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["2", 1]}},
        "8": {"class_type": PUBLISH, "inputs": {"images": ["7", 0]}},
    }


def two_branches():
    """One shared checkpoint, two samplers, one publish node each. Node 20 and node 30 publish."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "shared.safetensors"}},
        "10": {"class_type": "CLIPTextEncode",
               "inputs": {"text": "a wide desert", "clip": ["1", 1]}},
        "11": {"class_type": "KSampler",
               "inputs": {"seed": 111, "steps": 10, "cfg": 6.0, "sampler_name": "euler",
                          "model": ["1", 0], "positive": ["10", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["1", 2]}},
        "20": {"class_type": PUBLISH, "inputs": {"images": ["12", 0]}},
        "21": {"class_type": "CLIPTextEncode",
               "inputs": {"text": "a snowy street", "clip": ["1", 1]}},
        "22": {"class_type": "KSampler",
               "inputs": {"seed": 222, "steps": 30, "cfg": 9.0, "sampler_name": "heun",
                          "model": ["1", 0], "positive": ["21", 0]}},
        "23": {"class_type": "VAEDecode", "inputs": {"samples": ["22", 0], "vae": ["1", 2]}},
        "30": {"class_type": PUBLISH, "inputs": {"images": ["23", 0]}},
    }


def prompt_widget_no_sampler():
    """A cloud generator taking its words as widgets. No seed anywhere in the graph."""
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": "plate.png"}},
        "2": {"class_type": "KlingImageToVideo",
              "inputs": {"prompt": "the camera pushes in",
                         "negative_prompt": "text, watermark", "image": ["1", 0]}},
        "3": {"class_type": PUBLISH, "inputs": {"images": ["2", 0]}},
    }


def controlnet_advanced():
    """ControlNetApplyAdvanced takes both roles; the two prompts must not merge."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd15.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a marble statue", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low contrast",
                                                         "clip": ["1", 1]}},
        "4": {"class_type": "ControlNetLoader",
              "inputs": {"control_net_name": "depth_sd15.safetensors"}},
        "5": {"class_type": "LoadImage", "inputs": {"image": "depth.png"}},
        "6": {"class_type": "ControlNetApplyAdvanced",
              "inputs": {"strength": 0.8, "start_percent": 0.0, "end_percent": 1.0,
                         "positive": ["2", 0], "negative": ["3", 0], "control_net": ["4", 0],
                         "image": ["5", 0]}},
        "7": {"class_type": "KSampler",
              "inputs": {"seed": 9, "steps": 25, "cfg": 8.0, "sampler_name": "ddim",
                         "model": ["1", 0], "positive": ["6", 0], "negative": ["6", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
        "9": {"class_type": PUBLISH, "inputs": {"images": ["8", 0]}},
    }


def loaded_and_published(pinned=0):
    """An SG Load feeding an SG Publish. `pinned` is the widget-pinned Version id."""
    return {
        "1": {"class_type": LOAD, "inputs": {"project": "Sandbox", "link": "sh010 (Shot)",
                                             "pin_version_id": pinned}},
        "2": {"class_type": "ImageScale", "inputs": {"upscale_method": "lanczos",
                                                     "image": ["1", 0]}},
        "3": {"class_type": PUBLISH, "inputs": {"images": ["2", 0]}},
    }


# --- editor-format graphs, for instrument.py -----------------------------------------------------

def editor_two_previews():
    """Two named streams off one body, both feeding a preview: the descriptor must not collapse."""
    return {
        "nodes": [
            {"id": 1, "type": "DepthAnything", "title": "Depth",
             "outputs": [{"type": "IMAGE", "links": [1]}]},
            {"id": 2, "type": "NormalMap", "title": "Normal",
             "outputs": [{"type": "IMAGE", "links": [2]}]},
            {"id": 3, "type": "PreviewImage", "inputs": [{"type": "IMAGE"}], "outputs": []},
            {"id": 4, "type": "PreviewImage", "inputs": [{"type": "IMAGE"}], "outputs": []},
        ],
        "links": [[1, 1, 0, 3, 0, "IMAGE"], [2, 2, 0, 4, 0, "IMAGE"]],
    }


def editor_subgraph():
    """One subgraph instance: the node inside it is addressed `5/2`, and its output is a stream."""
    return {
        "nodes": [
            {"id": 5, "type": "sub-uuid", "title": "Depth Estimation (Depth Anything 3)",
             "inputs": [{"type": "IMAGE"}], "outputs": [{"type": "IMAGE", "links": [9]}]},
            {"id": 6, "type": "LoadImage", "outputs": [{"type": "IMAGE", "links": [8]}]},
            {"id": 7, "type": "SaveImage", "inputs": [{"type": "IMAGE"}], "outputs": []},
        ],
        "links": [[8, 6, 0, 5, 0, "IMAGE"], [9, 5, 0, 7, 0, "IMAGE"]],
        "definitions": {"subgraphs": [{
            "id": "sub-uuid", "name": "Depth",
            "inputNode": {"id": -10}, "outputNode": {"id": -20},
            "outputs": [{"name": "depth"}],
            "nodes": [{"id": 2, "type": "ImageInvert", "inputs": [{"type": "IMAGE"}],
                       "outputs": [{"type": "IMAGE", "links": [12]}]}],
            "links": [{"origin_id": -10, "origin_slot": 0, "target_id": 2, "target_slot": 0,
                       "type": "IMAGE"},
                      {"origin_id": 2, "origin_slot": 0, "target_id": -20, "target_slot": 0,
                       "type": "IMAGE"}],
        }]},
    }
