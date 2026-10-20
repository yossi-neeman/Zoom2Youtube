"""
Application version information
"""

VERSION = "1.4.0"
BUILD_DATE = "2026-10-20"
# Admin sign-in with Google (email allowlist) alongside password login

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
