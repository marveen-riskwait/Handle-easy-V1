"""QR code helpers.

A table's printed QR just encodes a public URL:
    {FRONTEND_URL}/table/<qr_token>
Scanning it drops the guest straight onto the split screen for that table.
"""
import io
import os
import base64
import secrets


def new_token():
    """A short, URL-safe, unguessable token for a table."""
    return secrets.token_urlsafe(9)


def table_url(qr_token):
    base = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/table/{qr_token}"


def qr_data_uri(qr_token):
    """Return the table URL rendered as an SVG data URI.

    SVG (pure-Python) avoids a Pillow/PNG build dependency. Kept
    import-local so a missing qrcode install degrades to just the URL
    rather than crashing the table endpoint. The returned `image` is a
    data URI usable directly as an <img src>.
    """
    url = table_url(qr_token)
    try:
        import qrcode
        import qrcode.image.svg
    except Exception:
        return {"url": url, "image": None}

    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage)
    buf = io.BytesIO()
    img.save(buf)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"url": url, "image": f"data:image/svg+xml;base64,{encoded}"}
