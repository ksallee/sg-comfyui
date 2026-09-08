"""Who the nodes talk to Flow PT as, and where that is kept.

Two ways in, and a person wins over a machine:

- **A person, signed in through the App Session Launcher** (probe 052). The operator clicks Sign in on
  a node, approves the request in the browser where they are already logged into Flow PT, and the
  session token the site hands back is kept in ComfyUI's protected user directory. Every Version is
  then created by that person, with no script key and no impersonation.
- **A script key from the environment**: `FPT_API_SITE_URL`, `FPT_API_SCRIPT_NAME`, `FPT_API_API_KEY`,
  from the launch environment or from `.env.local` in a checkout. The farm and the developer path.

The session file lives outside `custom_nodes/`, so a Manager update leaves it alone, and under a
`__` directory, which ComfyUI serves over no HTTP route (folder_paths.get_system_user_directory).
Outside ComfyUI it sits beside `.env.local`, gitignored by the same `*.local.json` rule.
"""
import json
import os
import platform
import time
from pathlib import Path

from sg_groundtruth import launcher
from sg_groundtruth.client import FPT, FPTError
from sg_groundtruth.env import load as load_env

ROOT = Path(__file__).resolve().parents[2]
PACK = "comfyui_flow_production_tracking"          # get_system_user_directory allows no hyphen
APP_NAME = "ComfyUI Flow Production Tracking"      # what the person sees on the approval page
FILE = "session.local.json"

# Approval requests this ComfyUI has open, by id. A request nobody approves is forgotten by the
# site after about five minutes (probe 052), so nothing here outlives a restart on purpose.
_pending = {}


def store_dir():
    """ComfyUI's protected per-pack directory, else the checkout root."""
    try:
        import folder_paths
        return Path(folder_paths.get_system_user_directory(PACK))
    except Exception:
        return ROOT


def session_path():
    return store_dir() / FILE


def read_session():
    """{site, session_token, login, approved_at}, or {} when nobody is signed in."""
    p = session_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_session(site, session_token, login):
    p = session_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"site": site.rstrip("/"), "session_token": session_token,
                             "login": login, "approved_at": time.time()}))
    os.chmod(p, 0o600)


def clear_session():
    try:
        session_path().unlink()
    except FileNotFoundError:
        pass


def env():
    return load_env(ROOT)


def how():
    """("person" | "script" | "none", site url, who). Never the key, never the token."""
    s = read_session()
    if s.get("session_token"):
        return "person", s.get("site", ""), s.get("login", "")
    e = env()
    if e.get("FPT_API_SITE_URL") and e.get("FPT_API_SCRIPT_NAME") and e.get("FPT_API_API_KEY"):
        return "script", e["FPT_API_SITE_URL"], e["FPT_API_SCRIPT_NAME"]
    return "none", e.get("FPT_API_SITE_URL", ""), ""


def client():
    """A connected client, as the person when one is signed in, else as the script."""
    kind, site, _ = how()
    if kind == "person":
        return FPT.from_session(site, read_session()["session_token"])
    if kind == "script":
        return FPT.from_env(env())
    raise FPTError("Not signed in to Flow Production Tracking. Click Sign in on the node.")


def status():
    """What the panel shows: who is signed in, to which site, and whether the site still agrees.

    `alive` costs one call to the site and is what turns a session the site forgot into a Sign in
    button rather than empty pickers.
    """
    kind, site, who = how()
    out = {"how": kind, "site": site, "who": who, "alive": kind == "script"}
    if kind == "person":
        s = launcher.alive(site, read_session()["session_token"])
        out["alive"] = bool(s) and not s.get("expired")
        if s:
            out["expires_at"] = s.get("expiresAt")
    return out


def begin(site):
    """Ask the site for a login. Returns {request_id, url}: the url is opened in the person's browser."""
    site = (site or "").strip().rstrip("/")
    if not site.startswith("https://"):
        raise FPTError("Enter the site address, starting with https://. "
                       "Example: https://yourstudio.shotgrid.autodesk.com")
    rid, url = launcher.request(site, APP_NAME, platform.node())
    _pending[rid] = site
    return {"request_id": rid, "url": url}


def finish(request_id):
    """One poll. {state: pending | approved | gone, who}. Approved writes the session and forgets caches."""
    site = _pending.get(request_id)
    if not site:
        return {"state": "gone"}
    try:
        token, login = launcher.poll(site, request_id)
    except launcher.Pending:
        return {"state": "pending"}
    except launcher.Gone:
        _pending.pop(request_id, None)
        return {"state": "gone"}
    _pending.pop(request_id, None)
    write_session(site, token, login)
    from . import site as _site
    _site.forget_all()
    return {"state": "approved", "who": login}
