"""Who the nodes talk to Flow PT as, and where that is kept.

Two ways in, and a person wins over a machine:

- **A person, signed in through the App Session Launcher** (probe 052). The operator clicks Log in
  under Settings, approves the request in the browser where they are already logged into Flow PT,
  and the session token the site hands back is kept in ComfyUI's protected user directory. Every
  Version is then created by that person, with no script key and no impersonation.
- **A script**: a script name and application key entered under Settings, else `FPT_API_SITE_URL`,
  `FPT_API_SCRIPT_NAME` and `FPT_API_API_KEY` from the launch environment or from `.env.local` in a
  checkout. A farm has no browser, and this is its path. A login beside the key makes the script
  publish as that person (probe 027, `sudo_as_login`).

Both files live outside `custom_nodes/`, so a Manager update leaves them alone, and under a `__`
directory, which ComfyUI serves over no HTTP route (folder_paths.get_system_user_directory). Outside
ComfyUI they sit beside `.env.local`, gitignored by the same `*.local.json` rule.
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
SESSION_FILE = "session.local.json"
SETTINGS_FILE = "settings.local.json"
SETTINGS_KEYS = ("site", "script_name", "api_key", "login")

SETUP = ("Not connected to Flow Production Tracking. Open Settings, then SG, and log in or "
         "enter a script name and application key.")

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


def _read(name):
    p = store_dir() / name
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _write(name, data):
    p = store_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
    os.chmod(p, 0o600)


def session_path():
    return store_dir() / SESSION_FILE


def read_session():
    """{site, session_token, login, approved_at}, or {} when nobody is signed in."""
    return _read(SESSION_FILE)


def write_session(site, session_token, login):
    _write(SESSION_FILE, {"site": site.rstrip("/"), "session_token": session_token,
                          "login": login, "approved_at": time.time()})


def clear_session():
    try:
        session_path().unlink()
    except FileNotFoundError:
        pass


def settings():
    """What the Settings dialog holds: {site, script_name, api_key, login}, any of them absent."""
    return _read(SETTINGS_FILE)


def save_settings(changes):
    """Merge what the dialog sent. A key it did not send is left alone; an empty string clears it."""
    cur = settings()
    for k in SETTINGS_KEYS:
        if k in changes:
            v = str(changes.get(k) or "").strip()
            cur[k] = v.rstrip("/") if k == "site" else v
    _write(SETTINGS_FILE, cur)


def env():
    return load_env(ROOT)


def site_url():
    """The site address, from Settings first and the environment second."""
    return (settings().get("site") or env().get("FPT_API_SITE_URL") or "").rstrip("/")


def script():
    """(script name, key, login, source). Settings first, the environment second, "" when neither."""
    s, e = settings(), env()
    login = s.get("login", "")
    if s.get("script_name") and s.get("api_key"):
        return s["script_name"], s["api_key"], login, "settings"
    if e.get("FPT_API_SCRIPT_NAME") and e.get("FPT_API_API_KEY"):
        return e["FPT_API_SCRIPT_NAME"], e["FPT_API_API_KEY"], login, "environment"
    return "", "", login, ""


def how():
    """("person" | "script" | "none", site url, who). Never the key, never the token."""
    s = read_session()
    if s.get("session_token"):
        return "person", s.get("site", ""), s.get("login", "")
    name, key, _, _ = script()
    site = site_url()
    if site and name and key:
        return "script", site, name
    return "none", site, ""


def client():
    """A connected client, as the person when one is signed in, else as the script."""
    kind, site, _ = how()
    if kind == "person":
        return FPT.from_session(site, read_session()["session_token"])
    if kind == "script":
        name, key, login, _ = script()
        return FPT(site, name, key, sudo_as_login=login)
    raise FPTError(SETUP)


def status():
    """What Settings shows: who the nodes publish as, the site, and whether the site still agrees.

    `alive` costs one call to the site and is what turns a session the site forgot into a Log in
    button rather than empty pickers. The script half is reported whether or not it is in use, so
    the dialog can show what it holds; the key itself is never in the answer.
    """
    kind, site, who = how()
    name, key, login, source = script()
    out = {"how": kind, "site": site_url() or site, "who": who, "alive": kind == "script",
           "script_name": name, "has_key": bool(key), "script_source": source, "login": login,
           # A name typed under Settings before its key arrives, so the dialog can show it.
           "typed_script_name": settings().get("script_name", "")}
    if kind == "person":
        s = launcher.alive(site, read_session()["session_token"])
        out["alive"] = bool(s) and not s.get("expired")
        if s:
            out["expires_at"] = s.get("expiresAt")
    return out


def test():
    """One round trip as whoever the nodes would publish as. {ok, who}; a refusal raises."""
    kind, _, who = how()
    c = client()
    r = c.get("")            # the root document, which needs no permission (probe 027)
    if not r.ok:
        raise FPTError(f"The site answered {r.status_code}. {r.text[:200]}")
    if kind == "person":
        return {"ok": True, "who": f"{who}, logged in"}
    _, _, login, _ = script()
    return {"ok": True, "who": f"script {who}" + (f", publishing as {login}" if login else "")}


def begin(site=""):
    """Ask the site for a login. Returns {request_id, url}: the url is opened in the person's browser."""
    site = (site or site_url()).strip().rstrip("/")
    if not site.startswith("https://"):
        raise FPTError("Enter the site address under Settings, starting with https://. "
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
