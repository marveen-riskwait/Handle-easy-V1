"""Small shared helpers: JSON error type and a dev sitemap."""


class APIException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def generate_sitemap(app):
    """A minimal HTML index of registered API endpoints (dev only)."""
    links = []
    for rule in app.url_map.iter_rules():
        if "GET" in (rule.methods or set()) and str(rule).startswith("/api"):
            links.append(str(rule))
    links_html = "".join(f"<li><code>{l}</code></li>" for l in sorted(set(links)))
    return (
        "<div style='font-family:sans-serif;padding:2rem'>"
        "<h1>Handle Easy API</h1>"
        "<p>Backend is running. Available GET endpoints:</p>"
        f"<ul>{links_html}</ul></div>"
    )
