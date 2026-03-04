"""URL normalization for OpenURL tool.

Each connector implements normalize_url() as a class method to normalize URLs to match
the canonical Document.id format used during ingestion. This ensures OpenURL can find
indexed documents.

Usage:
    normalized = normalize_url("https://docs.google.com/document/d/123/edit")
    # Returns: "https://docs.google.com/document/d/123"
"""

from urllib.parse import urlparse
from urllib.parse import urlunparse

from onyx.configs.constants import DocumentSource
from onyx.connectors.factory import identify_connector_class
from onyx.utils.logger import setup_logger

logger = setup_logger()


def _default_url_normalizer(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.netloc:
        return None

    # Strip query params and fragment, normalize trailing slash
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    params = ""  # URL params (rarely used)
    query = ""  # Query string (removed)
    fragment = ""  # Fragment/hash (removed)

    normalized = urlunparse((scheme, netloc, path, params, query, fragment))
    return normalized or None


def normalize_url(url: str, source_type: DocumentSource | None = None) -> str | None:
    """Normalize a URL to match the canonical Document.id format.

    Dispatches to the connector's normalize_url() method or falls back to default normalizer.
    """
    # If source_type not provided, try to detect it
    if source_type is None:
        source_type = _detect_source_type(url)

    if source_type:
        try:
            connector_class = identify_connector_class(source_type)
            result = connector_class.normalize_url(url)

            if result.use_default:
                return _default_url_normalizer(url)
            return result.normalized_url  # Could be None if failed
        except Exception as exc:
            logger.debug(
                "Failed to normalize URL for source %s: %s. Using default normalizer.",
                source_type,
                exc,
            )

    # No source_type or connector not found - fall back to default
    return _default_url_normalizer(url)


def _detect_source_type(url: str) -> DocumentSource | None:
    """Detect DocumentSource from URL patterns (simple heuristic)."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()

    if netloc == "docs.google.com" or netloc.endswith(".docs.google.com") or netloc == "drive.google.com" or netloc.endswith(".drive.google.com"):
        return DocumentSource.GOOGLE_DRIVE
    if netloc == "notion.so" or netloc.endswith(".notion.so") or netloc == "notion.site" or netloc.endswith(".notion.site"):
        return DocumentSource.NOTION
    if netloc == "atlassian.net" or netloc.endswith(".atlassian.net"):
        # Check path for Jira indicators (more specific than netloc)
        if "/jira/" in path or "/browse/" in path or "jira" in netloc:
            return DocumentSource.JIRA
        return DocumentSource.CONFLUENCE
    if netloc == "github.com" or netloc.endswith(".github.com"):
        return DocumentSource.GITHUB
    if netloc == "gitlab.com" or netloc.endswith(".gitlab.com"):
        return DocumentSource.GITLAB
    if netloc == "sharepoint.com" or netloc.endswith(".sharepoint.com"):
        return DocumentSource.SHAREPOINT
    if netloc == "slack.com" or netloc.endswith(".slack.com"):
        return DocumentSource.SLACK
    if netloc == "linear.app" or netloc.endswith(".linear.app"):
        return DocumentSource.LINEAR

    return None
