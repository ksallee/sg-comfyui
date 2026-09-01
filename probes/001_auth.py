"""Q: does client_credentials work, and how long does a token actually live?"""
import _lib

env = _lib.load_env()
c = _lib.client()

r = c.get("/entity/projects", params={"fields": "name", "page[size]": 1})
actual = f"status {r.status_code}\ntoken lifetime (expires_at - now): {c._expires_at:.0f}\n\n{_lib.dump(r.json() if r.ok else r.text)}"

_lib.record(
    "001_auth",
    "POST /api/v1/auth/access_token  +  GET /api/v1/entity/projects",
    "client_credentials with script name/key returns a bearer token; expires_in documented as 600s.",
    actual,
    "TBD — fill in after running.",
    env,
)
