"""
Application version information
"""

VERSION = "1.3.2"
BUILD_DATE = "2026-10-19"
# Changed: default Dockerfile is now the regular web-app image; Lambda image moved to Dockerfile.lambda

def get_version():
    """Get the current application version"""
    return VERSION

def get_full_version():
    """Get full version with build date"""
    return f"v{VERSION} ({BUILD_DATE})"
