---
description: Walk a first run of the SG nodes on this ComfyUI, from connection to the example workflow
---

Installing is `README.md`. This command checks each thing a first run needs, in the order it is
needed, and asks only what it cannot find out.

0. **Run the doctor.** `<comfy-python> tools/doctor.py`, with the interpreter ComfyUI runs on. It
   prints one line per check with the fix appended where it fails: the interpreter and whether the
   client imports there, the pack directory, which profile path is in force, and which local files
   exist. Read its `fail` lines back before doing anything else. `--site` adds the connection, the
   provenance fields, the storage roots and the link types, and needs `.env.local`.
1. **Is ComfyUI connected?** Open Settings, then SG. **Test** reports the site's own answer, and the
   Log In As Yourself group says who is logged in. A 404 from the dialog means the running ComfyUI
   started before the pack was installed: restart it, then reload the page. If it persists, check the
   ComfyUI version, because 0.34.0 is the floor. Say which of the two credential paths applies, and
   do not offer the other:
   - **A person at a workstation** clicks **Log in**, approves the request in the browser tab that
     opens, and the Versions are created by them. No key is entered anywhere.
   - **A render farm, or a machine nobody signs in on**, has no browser. It takes a Script name and
     Application key under Script Authentication, made under Admin > Scripts on the site, or the
     same three keys in the launch environment (`.env.local.example` names them). Publish as is
     optional and names the person the Versions are credited to.
   The command-line tools read `.env.local` in the pack directory, never Settings, so a checkout that
   runs them needs the script key even when the editor is logged in.
2. **Pick the project.** Settings, then SG, SG Defaults. Both nodes open on it, and the publish
   defaults under it are for that project.
3. **Does the profile match their show?** `profile.local.json`, keyed per project, at the path the
   doctor printed. It is gitignored, so a fresh install has none, and the pickers then run on the
   site's own defaults, which suit a show that links Versions to Shots. Run `/inspect-site
   <project>` when the show names its Versions to a convention, links them to something else, or
   hides statuses the schema still lists. Nothing needs it before a first publish.
4. **Provenance fields.** Settings, then SG, SG Site Setup says how many of the nine exist on this
   site, and one press creates the rest. It needs an account that can create fields on Version, which
   most artist accounts cannot; a farm or a checkout runs `PYTHONPATH=src <comfy-python> -m
   comfyui_sg.fields` instead. Without the fields a publish records the facts in the Version's
   description instead.
5. **Colour management.** Core ComfyUI has none, and the shipped templates use core nodes only. Ask
   once whether this pipeline is colour managed. If yes: install the
   [ComfyUI-OCIO](https://github.com/SlavaSexton/ComfyUI-OCIO) pack, set
   `OPENCV_IO_ENABLE_OPENEXR=1` in the environment that launches ComfyUI, and check that `ffmpeg`
   is on the path. If no, say nothing more about it.
6. **Open the example.** Templates browser, category **sg-comfyui**, `00_example`. It opens on the
   Settings project. Its note says what each half does: the Publish half runs as it is and sends
   nothing until a project and a link are picked, and Create Published Files is off so nothing is
   written to disk. Restart ComfyUI only to install or upgrade the pack. A later edit to the
   profile is read on a browser refresh.

Then `/track-workflow <workflow.json>` for a graph they already use.
