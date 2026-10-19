"""
Application version information
"""

VERSION = "1.3.3"
BUILD_DATE = "2026-10-19"
# Security: gunicorn instead of Flask debug server, login rate limiting, hardened cookies/CORS, non-root container

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
