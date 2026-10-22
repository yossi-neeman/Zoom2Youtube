"""
Application version information
"""

VERSION = "1.5.1"
BUILD_DATE = "2026-10-22"
# Remove the unused AWS Lambda deployment files

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
