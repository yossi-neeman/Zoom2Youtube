"""
Application version information
"""

VERSION = "1.5.0"
BUILD_DATE = "2026-10-22"
# Google sign-in hand-off for the native Android app (z2y:// redirect + /auth/app-exchange)

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
