"""Which REST requests the sidebar's relay forwards to the site, and what crosses with them.

The sidebar runs sg-widgets' `RestClient` in the browser against `/sg/rest`. The route in
`routes.py` forwards an allowed request with this ComfyUI's credentials. Reads only: a request
that could write is refused before it reaches the site.
"""
import re

_NAME = r"[A-Za-z0-9_]+"
_ROUTE = r"[a-z0-9_]+"

# (method, path under /api/v1). One line per read the widgets make.
_ALLOWED = [
    ("GET", re.compile(r"/schema")),
    ("GET", re.compile(rf"/schema/{_NAME}/fields")),
    ("GET", re.compile(rf"/schema/{_NAME}/fields/{_NAME}")),
    ("GET", re.compile(rf"/entity/{_ROUTE}/\d+")),
    ("GET", re.compile(r"/entity/statuses")),
    ("POST", re.compile(rf"/entity/{_ROUTE}/_search")),
    ("POST", re.compile(r"/entity/_text_search")),
]

# The filter shape decides the Content-Type, and the two are not interchangeable (probe 030).
_FORWARDED_HEADERS = ("Content-Type",)


def allowed(method, path):
    """True when `method` and `path`, under /api/v1, are one of the reads above."""
    return any(m == method and rx.fullmatch(path) for m, rx in _ALLOWED)


def forward_headers(headers):
    """The request headers sent on to the site. Credentials come from this ComfyUI, not the browser."""
    lowered = {k.lower(): v for k, v in headers.items()}
    return {h: lowered[h.lower()] for h in _FORWARDED_HEADERS if h.lower() in lowered}


def refusal(method, path):
    """A JSON:API error body for a request the relay does not forward."""
    return {"errors": [{
        "status": 403,
        "title": "The sidebar reads only.",
        "detail": f"The relay does not forward {method} {path}.",
    }]}
