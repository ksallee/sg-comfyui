# Install and operate

README.md is what the nodes do and the first run. This file is the local files, the interpreter, the
command-line tools, the profile key by key, and the fixes.

## The interpreter

Install the requirements into the interpreter ComfyUI itself runs on.

| install | the interpreter |
|---|---|
| source | `ComfyUI/venv/bin/python` |
| desktop | the `python` inside the app bundle |
| studio | whatever your launch script names |

Installing into a different one leaves the pack loaded, the pickers empty, and no error naming a
cause. Check which one you have:

```sh
cd ComfyUI/custom_nodes/sg-comfyui
../../venv/bin/python tools/doctor.py
```

```
ok    Python 3.11.11 at /Users/you/ComfyUI/venv/bin/python.
ok    sg_groundtruth imports here.
ok    requests imports here.
ok    Pillow imports here.
ok    This is the interpreter ComfyUI runs on, /Users/you/ComfyUI/venv/bin/python.
```

- A `fail` line names the fix.
- `--site` adds the connection, the provenance fields, the storage roots and the link types.
- `COMFYUI_PATH` tells the doctor where ComfyUI is. It defaults to `~/dev/ComfyUI`.
- The doctor exits non-zero on anything that would fail a publish. It warns on the rest.

The API client is `sg-groundtruth`, from PyPI. `requirements.txt` names it. Every install path
installs that file.

## Signing in

Both paths are under Settings, then SG.

**A person, at a workstation.** Press Log in under Log In As Yourself. Approve the request in the
browser tab. The nodes publish as you.

**A script, on a farm or a machine nobody signs in on.** Make the script under Admin, then Scripts,
in Flow Production Tracking. Enter its Script name and Application key under Script Authentication.
The script needs read on Projects, Versions, Tasks and every entity type you link Versions to, plus
create on Version and upload of media.

Press Test either way. It reports who the nodes publish as.

## Creating the provenance fields

Do this to make the nine AI fields queryable on Version, in a filter or a page layout. A publish
never needs them: a site with none of them records every fact in the Version's description.

Open Settings, then SG, SG Site Setup. It reports how many of the nine exist. Press Create to add the
rest.

Run the same thing from a farm or a checkout with no browser on it:

```sh
PYTHONPATH=src <comfy-python> -m comfyui_sg.fields
```

- It reads the schema first and creates only what is missing. Pressing twice is safe.
- It imports no torch.
- It reads a script key from `.env.local`, never from Settings.
- That key needs permission to create fields on Version. Most artist accounts do not have it.
- Field names are permanent. Deleting a field frees the field, never its name. Trashed fields cannot
  be listed, so a name spent here is spent site-wide forever (probe 019).
- Pointing the profile's `provenance.map` at fields your studio already has is the preferred move.

## Colour management

Core ComfyUI has none. The shipped templates use core nodes only. None of this is needed to publish.

For a colour-managed pipeline:

1. Install the [ComfyUI-OCIO](https://github.com/SlavaSexton/ComfyUI-OCIO) pack.
2. Set `OPENCV_IO_ENABLE_OPENEXR=1` in the environment that launches ComfyUI.
3. Put `ffmpeg` on the path.

## Where the local files live

Four files, all of them yours, none of them in git.

| file | holds | written by | read from |
|---|---|---|---|
| `settings.local.json` | site address, script name, application key, publish as | Settings, then SG | the protected user directory |
| `session.local.json` | the session token from Log in | Settings, then SG | the protected user directory |
| `profile.local.json` | what your site practices, per project | the inspector, Settings, and you | the protected user directory, else the pack directory |
| `.env.local` | a script key for the command-line tools | you | the pack directory |

The **protected user directory** is `<ComfyUI user directory>/__sg_comfyui`. That is
`ComfyUI/user/__sg_comfyui` unless `--user-directory` or `--base-directory` moved it. It sits outside
`custom_nodes`, so an upgrade leaves it alone, and ComfyUI serves a `__` directory over no HTTP route.

The **pack directory** is where this repo's files are.

| install | the pack directory |
|---|---|
| git clone into `custom_nodes` | `ComfyUI/custom_nodes/sg-comfyui` |
| ComfyUI Manager or the Registry | `ComfyUI/custom_nodes/sg-comfyui`, made by the installer |
| a symlinked developer checkout | the real checkout, for example `~/dev/sg-comfyui` |

Which copy is read:

- **Settings and the session** come from the protected user directory. A command-line tool falls back
  to the pack directory, because outside a running ComfyUI there is no such directory.
- **The profile** comes from the protected user directory when a `profile.local.json` is there, and
  from the pack directory otherwise. Settings writes wherever that resolves to.
- Once a profile exists in the protected user directory, a second one in the pack directory is
  ignored. `tools/doctor.py` prints the path that won. Write to that path.

## Running the command-line tools

They run from the pack directory. On a Registry or Manager install, `cd` into it first:

```sh
cd ComfyUI/custom_nodes/sg-comfyui
```

| command | needs |
|---|---|
| `<comfy-python> tools/doctor.py [--site]` | nothing without `--site` |
| `<comfy-python> src/comfyui_sg/instrument.py <wf.json>` | nothing: no site, no profile, no torch |
| `PYTHONPATH=src <comfy-python> -m comfyui_sg.fields` | `.env.local` |
| `PYTHONPATH=src <comfy-python> -m comfyui_sg.seed <file> ...` | `.env.local`, `profile.local.json` |

- `PYTHONPATH=src` is required for every `-m comfyui_sg.*`. The package lives under `src/` and nothing
  installs it.
- `instrument.py` and `doctor.py` are run as files. `-m` would import the package `__init__` and
  therefore torch, and both must run on a machine with neither torch nor a route to the site.
- None of these needs torch. A plain Python with `requirements.txt` installed runs all of them.
- None of these reads Settings. They read `.env.local` in the pack directory, or the same three keys
  in the environment.

A workstation signed in through Log in still needs a script name and key for these:

```sh
cp .env.local.example .env.local        # then fill in the three keys
```

`.env.local` is gitignored, never printed and never logged. A missing key is reported by name, never
by value. On a farm, put the same three keys in the launch environment instead.

## Measuring a site without an agent

`/inspect-site` is a procedure an agent follows. The inspector under it is a script in the
`sg-groundtruth` checkout. Run it yourself instead.

Clone that checkout anywhere except `custom_nodes`, where ComfyUI would load it as a node pack:

```sh
git clone https://github.com/ksallee/sg-groundtruth.git ~/dev/sg-groundtruth
cp ~/dev/sg-groundtruth/.env.local.example ~/dev/sg-groundtruth/.env.local   # then fill it in
```

Run it with the interpreter that has the client installed, which is the one ComfyUI runs on:

```sh
<comfy-python> ~/dev/sg-groundtruth/inspect_site.py                                # list the projects
<comfy-python> ~/dev/sg-groundtruth/inspect_site.py --project 1180 --out <profile> # measure one
```

- The inspector reads credentials from its own `.env.local`, in its own checkout. The same three keys
  either way.
- Pass `--out`. Its default is `./profile.local.json` relative to the working directory, and the file
  has to land on the path `tools/doctor.py` reports.
- Read the report before accepting it. The link field is the value it most often gets wrong.
- The code convention comes with a coverage number saying how much of the show agrees with it.
- Re-running keeps your edits and prints `(yours, kept)` beside each value it would have changed.
  `--overwrite` discards them.

## The profile, on one page

`profile.local.json` is plain JSON and hand-editing it is expected. Top-level keys are the site
default. A `projects` block overrides them per show, so two graphs in one ComfyUI can publish into two
projects that name Versions differently.

```json
{
  "default_project": 1180,
  "projects": {
    "1180": {
      "link_type": "Shot",
      "link_field": "entity",
      "root_name": "{entity}_{sg_task.Task.step.Step.short_name}",
      "code_template": "{root_name}_v{version:03d}",
      "status": "rev",
      "published_files": {
        "storage": "primary",
        "path_template": "{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}",
        "movie_path_template": "{entity}/{root_name}/{version_name}{ext}",
        "register_movie": false,
        "colour_space": "sRGB"
      }
    }
  }
}
```

Site-wide:

| key | default | written by |
|---|---|---|
| `default_project` | none, and both nodes then ask | Settings, then SG, SG Defaults |
| `show_all_projects` | `false`, so template, demo and archived shows stay out of the picker | you |

Per project, and valid at the top level as a site default:

| key | default | written by |
|---|---|---|
| `link_type` | `Shot`, the type a bare link name means | the inspector |
| `link_field` | `entity`, the Version field the link is written to | the inspector |
| `link_types` | the types this show's Versions already use, most used first | you |
| `root_name` | `{entity}_{sg_task.Task.step.Step.short_name}` | Settings, SG Publish Defaults |
| `code_template` | `{root_name}_v{version:03d}` | Settings, SG Publish Defaults |
| `code_regex` | derived from the version name template | the inspector |
| `status` | none, so the site sets its own | Settings, SG Publish Defaults |
| `version_number_field` | none, so the version number lives inside the name | you |
| `widgets` | what `src/comfyui_sg/widgets.py` declares | you |
| `provenance` | `{"mode": "fields"}`, the nine fields by their own names | you |

Inside `published_files`:

| key | default | written by |
|---|---|---|
| `default` | `false`, so Create Published Files starts unticked | Settings, SG Publish Defaults |
| `storage` | none, and the only Local File Storage when the site has exactly one | Settings, Storage |
| `path_platform` | this machine's | Settings, Operating system |
| `path_template` | `{entity}/{root_name}/{version_name}/{version_name}.%04d{ext}` | Settings, Sequence path |
| `movie_path_template` | `{entity}/{root_name}/{version_name}{ext}` | Settings, Movie path |
| `register_movie` | `false`, so a clip beside frames is review only | Settings, Review movie |
| `path_to_frames` | `true` | Settings, Path to Frames |
| `path_to_movie` | `true` | Settings, Path to Movie |
| `colour_space` | none, so a publish declares nothing | Settings, Colour space |

`code_regex` and `link_types` are the two the inspector fills that Settings never shows.
`version_number_field`, `widgets` and `provenance` are hand-written. DESIGN.md says what each is for.

A template is written in Flow Production Tracking's own vocabulary:

- Dotted field paths to any depth: `{entity.Shot.code}`.
- Python's whole format spec: `{version:03d}`.
- `[optional blocks]`, which vanish when their fields are empty.
- Printf padding, `v%04d`, as a synonym for a version spec.
- A token with no value drops out with its separator.

`tools/doctor.py` renders every template in the profile against a sample publish. It names any token
that comes back with nothing.

## When something does not answer

**The Settings dialog says 404.** The running ComfyUI started before the pack was installed, so it
registered no routes. Restart ComfyUI and reload the page. If it still says 404, read the startup log
for the pack: a pack whose import failed registers nothing.

**The pickers are empty.** Open Settings, then SG, and press Test. An empty project list with a
passing Test means the account can see no project. A passing Test and an empty link list means this
project has no entity of that type yet.

**A new Shot, Task or Version does not show up.** The editor's lookups are cached for 600 seconds.
Press **Sync from SG** on the node to force a read.

**Nothing works and the pack looks installed.** Run `tools/doctor.py` with the interpreter ComfyUI
runs on. It names both interpreters when they differ.

**Create Published Files refuses, and the site has no storage.** Add a Local File Storage under Site
Preferences, then File Management, in Flow Production Tracking. Name it under Settings, then SG,
Storage. Until then, untick Create Published Files and publish review media.

**The storage root is not mounted.** The publish stops before the Version exists and names the root.
Mount it, or name a storage this machine can see.

**Versions read `ComfyUI (unknown client)`.** The client that POSTed `/prompt` did not name itself.
The name is the client's own claim, in `extra_data.comfy_usage_source`, and ComfyUI passes it to the
node as the hidden `COMFY_USAGE_SOURCE`. The standard frontend sends `comfyui-frontend`. Set it in
your own submitter:

    POST /prompt  {"prompt": {...}, "extra_data": {"comfy_usage_source": "my-farm-submitter"}}

A `Comfy-Usage-Source` header works too. The server copies it into `extra_data` only when the body
left the key out (`server.py:1120`).

**A publish failed after the frames were copied.** The copies stay where they are and the error names
their paths. Nothing is deleted, so a second attempt costs a copy rather than a re-render.
