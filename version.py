"""
Application version information
"""

VERSION = "1.3.1"
BUILD_DATE = "2026-10-19"
# Fixed: duplicate /api/upload no longer fails with "Video file not found" after a successful upload

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
