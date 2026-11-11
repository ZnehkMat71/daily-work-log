# Security Review

## Scope

Focused review of the Flask application's database restore flow, form protections,
SQLite query handling, upload validation, filesystem paths, error handling, and
secret configuration.

## Finding

| Severity | Confidence | Location | Finding |
|---|---:|---|---|
| Medium | 9/10 | `app.py` restore route and `templates/database_management.html` restore form | Database restoration had no CSRF protection or authentication. A cross-site request could attempt to replace the database when the local service is reachable, and the endpoint did not establish that its caller was authorized. |

## Recommended handling

- Add session-bound CSRF protection to state-changing forms and validate tokens on
  POST requests.
- Keep the application bound to localhost for its intended single-user local use.
- Do not expose the restore feature through a network-facing deployment without
  adding authentication and access control.

## Remediation status

- Session-bound CSRF validation is applied to all POST requests and tokens are
  included in the add, edit, delete, and restore forms.
- Database management routes reject non-loopback clients, and the built-in
  server binds to `127.0.0.1`.
- A private, ignored local Flask signing key is generated when
  `FLASK_SECRET_KEY` is not configured.
- The application still has no accounts. Do not expose it to a network without
  adding authentication and access control.
