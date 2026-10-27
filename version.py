"""
Application version information
"""

VERSION = "1.6.0"
BUILD_DATE = "2026-10-27"
# Add the native Android app (android/)

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
