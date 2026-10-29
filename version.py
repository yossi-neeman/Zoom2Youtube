"""
Application version information
"""

VERSION = "1.7.0"
BUILD_DATE = "2026-10-29"
# One-shot publish (Zoom download + YouTube upload as one job) and API-token access for cron

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
