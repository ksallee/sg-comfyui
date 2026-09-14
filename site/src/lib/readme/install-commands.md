### 1. From the Registry

Pick this to use the nodes. Manager updates the pack, and Settings and the profile keep your
configuration across updates: project, templates, storage, the provenance mapping, which inputs
are advanced. The pack is in alpha. What is missing is under What's next.

Open **Manager**, then **Custom Nodes Manager**. Search for `Flow Production Tracking`. Press
**Install**. Restart ComfyUI.

With the Comfy CLI, the pack is `sg-comfyui` at https://registry.comfy.org/nodes/sg-comfyui:

```sh
comfy node install sg-comfyui
```

Restart ComfyUI.

The commands `/setup`, `/task` and `/track-workflow` are in the pack, at
`ComfyUI/custom_nodes/sg-comfyui`. Start your agent in that directory to use them.

### 2. From the repo

Pick this to change the nodes. The checkout has the tests, the harness and the history an agent
works with, and your change survives `git pull`. It is also where `/inspect-site` runs, since it
needs the sg-groundtruth checkout beside it.

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

Start your agent in the checkout. The four commands are there, `/inspect-site` included.
