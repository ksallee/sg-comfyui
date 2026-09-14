### Which install

| install | what you get | updates |
|---|---|---|
| ComfyUI Manager or the Registry | the pack as released | Manager. An edit inside the pack is lost at the next update |
| A checkout | the repository: the pack, the tests, the tools, the site. Customize it with an agent, run the suite, fork it | `git pull` |

Both include `CLAUDE.md` and the commands under `.claude/commands/`, so `/setup`, `/inspect-site`,
`/task` and `/track-workflow` run from either.

### ComfyUI Manager

Open **Manager**, then **Custom Nodes Manager**. Search for `Flow Production Tracking`. Press
**Install**. Restart ComfyUI.

### The Registry

The pack is `sg-comfyui` at https://registry.comfy.org/nodes/sg-comfyui. With the Comfy CLI:

```sh
comfy node install sg-comfyui
```

Restart ComfyUI.

### A checkout

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
