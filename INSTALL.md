# Install and operate

README.md is the first run. This is where the files are, which interpreter runs what, and what to do
when something does not answer.

## The interpreter

The pack runs inside ComfyUI, so its dependencies belong to the interpreter ComfyUI itself runs on.
That is `ComfyUI/venv/bin/python` in a source install, the `python` inside the app bundle in a desktop
install, and whatever your launch script names in a studio install. Installing into a different one is
the failure that looks like nothing: the pack loads, the pickers stay empty, and no error names a
cause.

One command proves it:

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

A `fail` line names the fix. `COMFYUI_PATH` tells the doctor where ComfyUI is when it is not
`~/dev/ComfyUI`. Run it with `--site` to add the connection, the provenance fields, the storage roots
and the link types. It exits non-zero on anything that would fail a publish, and warns on the steps
you do not need to publish.

## Where the local files live

Four files, all of them yours, none of them in git.

| file | holds | written by | read from |
|---|---|---|---|
| `settings.local.json` | site address, script name, application key, publish as | Settings, then SG | the protected user directory |
| `session.local.json` | the session token from Log in | Settings, then SG | the protected user directory |
| `profile.local.json` | what your site practices, per project | the inspector, Settings, and you | the protected user directory, else the pack directory |
| `.env.local` | a script key for the command-line tools | you | the pack directory |

The **protected user directory** is `<ComfyUI user directory>/__sg_comfyui`, which is
`ComfyUI/user/__sg_comfyui` unless `--user-directory` or `--base-directory` moved it. It sits outside
`custom_nodes`, so an upgrade leaves it alone, and ComfyUI serves a `__` directory over no HTTP route,
so nobody on the port can read the key.

The **pack directory** is where this repo's files are:

| install | the pack directory |
|---|---|
| git clone into `custom_nodes` | `ComfyUI/custom_nodes/sg-comfyui` |
| ComfyUI-Manager or the Registry | `ComfyUI/custom_nodes/sg-comfyui`, made by the installer |
| a symlinked developer checkout | the real checkout, for example `~/dev/sg-comfyui`, because the path is resolved through the symlink |

Two resolution orders decide which copy is read:

- **Settings and the session** are read from the protected user directory. Outside a running ComfyUI
  there is no such directory, so a command-line tool falls back to the pack directory.
- **The profile** is read from the protected user directory when a `profile.local.json` is there, and
  from the pack directory otherwise. Settings writes wherever that resolves to, so a Registry install,
  which has no checkout to write into, still has somewhere to keep it.

That order has one consequence worth knowing before you meet it: once a profile exists in the
protected user directory, a second one in the pack directory is ignored. `tools/doctor.py` prints the
path that won, and that is the path to write.

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

`PYTHONPATH=src` is required for every `-m comfyui_sg.*`, because the package lives under `src/` and
nothing installs it. `instrument.py` and `doctor.py` are run as files on purpose: `-m` would import
the package `__init__` and therefore torch, and both must work on a machine that has neither torch nor
a route to the site. None of these needs torch, so a plain Python with `requirements.txt` installed
runs all of them.

**The command-line tools never read Settings.** They read `.env.local` in the pack directory, or the
same three keys in the environment. A workstation where somebody is signed in through Log in still
needs a script name and key for these:

```sh
cp .env.local.example .env.local        # then fill in the three keys
```

`.env.local` is gitignored and never printed or logged. A missing key is reported by name, never by
value. On a farm, put the same three keys in the launch environment instead.

## Measuring a site without an agent

`/inspect-site` is a procedure an agent follows. The inspector underneath it is a script, and you can
run it yourself. It lives in the `sg-groundtruth` checkout, not in this pack, because that repo owns
site measurement.

Put that checkout **anywhere except `custom_nodes`**, where ComfyUI would try to load it as a node
pack. Beside this one is the convention:

```sh
git clone https://github.com/ksallee/sg-groundtruth.git ~/dev/sg-groundtruth
cp ~/dev/sg-groundtruth/.env.local.example ~/dev/sg-groundtruth/.env.local   # then fill it in
```

The inspector reads credentials from **its own** `.env.local`, in its own checkout, not this pack's.
The same three keys either way.

```sh
<comfy-python> ~/dev/sg-groundtruth/inspect_site.py                                # list the projects
<comfy-python> ~/dev/sg-groundtruth/inspect_site.py --project 1180 --out <profile> # measure one
```

Use the interpreter that has the client installed, which is the one ComfyUI runs on. The inspector
imports `sg_groundtruth` like everything else here.

`--out` is not optional in practice: its default is `./profile.local.json` relative to the working
directory, and the file has to land on the path `tools/doctor.py` reports. Read the report it prints
before you accept it. The link field is the value it most often gets wrong, and the code convention
comes with a coverage number that says how much of the show agrees with it.

Re-running keeps your edits and prints `(yours, kept)` beside each value it would have changed.
`--overwrite` discards them.

## The profile, on one page

`profile.local.json` is plain JSON and hand-editing it is expected. Top-level keys are the site
default; a `projects` block overrides them per show, which is what lets two graphs in one ComfyUI
publish into two projects that name Versions differently.

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
`version_number_field`, `widgets` and `provenance` are hand-written, and DESIGN.md says what each one
is for.

A template is written in Flow Production Tracking's own vocabulary: dotted field paths to any depth
(`{entity.Shot.code}`), Python's whole format spec (`{version:03d}`), `[optional blocks]` that vanish
when their fields are empty, and printf padding (`v%04d`) as a synonym for a version spec. A token
with no value drops out with its separator. `tools/doctor.py` renders every template in the profile
against a sample publish and names any token that comes back with nothing.

## When something does not answer

**The Settings dialog says 404.** The ComfyUI that is running started before the pack was installed,
so it registered none of its routes. Restart ComfyUI, then reload the page. If it still says 404,
check the startup log for the pack: a pack whose import failed registers nothing, and the traceback
is in that log.

**The pickers are empty.** Open Settings, then SG, and press Test. It reports the site's own answer.
An empty project list with a passing Test means the account cannot see any project; a passing Test and
an empty link list means this project has no entity of that type yet.

**A new Shot, Task or Version does not show up.** The editor's lookups are cached for 600 seconds,
because they run on every page load. Press **Sync from SG** on the node, which forces a read.

**Nothing works and the pack looks installed.** Run `tools/doctor.py` with the interpreter ComfyUI
runs on. Installing the requirements into a different Python is the common cause, and the doctor names
both interpreters.

**Create Published Files refuses, and the site has no storage.** Published Files must sit under a Local
File Storage root, and the server refuses any other path. Add one under Site Preferences, then File
Management, in Flow Production Tracking, and name it under Settings, then SG, Storage. Until then,
untick Create Published Files and publish review media.

**The storage root is not mounted.** The publish stops before the Version exists, and names the root.
Mount it, or name a storage this machine can see.

**Versions read `ComfyUI (unknown client)`.** The client that POSTed `/prompt` did not name itself.
The standard ComfyUI frontend does; a script of your own does when it sends
`extra_data.comfy_usage_source`, or a `Comfy-Usage-Source` header. README.md, "Where provenance
lands", has the shape.

**A publish failed after the frames were copied.** The copies are left where they are and the error
names their paths. Nothing is deleted, so a second attempt costs a copy rather than a re-render.
