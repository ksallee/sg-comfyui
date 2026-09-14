### 1. From the Registry

The pack as released. ComfyUI Manager updates it. An edit inside the pack is lost at the next
update.

Open **Manager**, then **Custom Nodes Manager**. Search for `Flow Production Tracking`. Press
**Install**. Restart ComfyUI.

With the Comfy CLI, the pack is `sg-comfyui` at https://registry.comfy.org/nodes/sg-comfyui:

```sh
comfy node install sg-comfyui
```

Restart ComfyUI.

### 2. From the repo

The repository: the pack, the tests, the tools, the site. Customize it with an agent, run the
suite, fork it. `git pull` updates it.

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/ksallee/sg-comfyui.git
cd sg-comfyui
<comfy-python> -m pip install -r requirements.txt
```

Restart ComfyUI.

`<comfy-python>` is the interpreter ComfyUI runs on. Check the install with it:

```sh
<comfy-python> tools/doctor.py
```

Both include `CLAUDE.md` and the commands under `.claude/commands/`, so `/setup`, `/inspect-site`,
`/task` and `/track-workflow` run from either.
