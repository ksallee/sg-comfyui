---
description: Walk a first run of the SG nodes on this ComfyUI, from connection to the example workflow
---

Nothing to install here beyond what `README.md` says. This command checks each thing a first run
needs, in the order it is needed, and asks only what it cannot find out.

1. **Is ComfyUI connected?** Open Settings, then SG. **Test** reports the site's own answer, and the
   Log In As Yourself group says who is logged in. A 404 from the dialog means the running ComfyUI
   predates the pack: restart it, then reload the page. Say which of the two credential paths
   applies, and do not offer the other:
   - **A person at a workstation** clicks **Log in**, approves the request in the browser tab that
     opens, and every Version is created by them. No key is entered anywhere.
   - **A render farm, or a machine nobody signs in on**, has no browser. It takes a Script name and
     Application key under Script Authentication, made under Admin > Scripts on the site, or the
     same three keys in the launch environment (`.env.local.example` names them). Publish as is
     optional and names the person the Versions are credited to.
   The command-line tools in `README.md` read `.env.local` in this checkout, never Settings, so a
   checkout that runs them needs the script key even when the editor is logged in.
2. **Does the profile exist for their project?** `profile.local.json` at the repo root, keyed per
   project. It is gitignored, so a fresh clone has none. Without a block for the project the
   pickers still work on the site's defaults, which carry a Shot-linked show; anything else, and the
   naming convention, come from `/inspect-site <project>`. Run it before going further when the
   block is missing.
3. **Colour management.** Core ComfyUI has none, and the shipped templates use core nodes only. Ask
   once whether this pipeline is colour managed. If yes: install the
   [ComfyUI-OCIO](https://github.com/SlavaSexton/ComfyUI-OCIO) pack, set
   `OPENCV_IO_ENABLE_OPENEXR=1` in the environment that launches ComfyUI, and check that `ffmpeg`
   is on the path. If no, say nothing more about it; nothing here needs it.
4. **Open the example.** Templates browser, category **sg-comfyui**, `00_example`. It opens on the
   Settings project. Its note says what each half does: the Publish half runs as it is and sends
   nothing until a project and a link are picked, and Create Published Files is off so nothing is
   written to disk. Restart ComfyUI only for installing or upgrading the pack; a later edit to the
   profile reaches the editor on a browser refresh.

Then, in order: `PYTHONPATH=src python -m comfyui_sg.fields` once per site, and `/track-workflow`
for a graph they already use.
