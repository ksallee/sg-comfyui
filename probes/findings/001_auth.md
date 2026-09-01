# 001_auth

**Endpoint** `POST /api/v1/auth/access_token  +  GET /api/v1/entity/projects`

**Docs claim** client_credentials with script name/key returns a bearer token; expires_in documented as 600s.

**Actual**

```
POST auth -> 200
payload keys/values: {
  "token_type": "Bearer",
  "access_token": "<str, 415 chars>",
  "expires_in": 600,
  "refresh_token": "<str, 527 chars>"
}

GET /entity/projects -> 200
projects: [(63, 'Start From Scratch'), (70, 'Big Buck Bunny'), (78, 'Game Template')]
```

**Verdict** Docs correct. `expires_in` is 600s. A `refresh_token` is returned; the client ignores it and
re-authenticates instead — 600s comfortably outlives a single publish and refresh is one more failure mode.
