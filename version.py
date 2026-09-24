"""
Application version information
"""

VERSION = "1.3.0"
BUILD_DATE = "2026-09-24"
# Added: Login screen with session-based authentication

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
