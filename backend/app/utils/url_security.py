"""URL security utilities — SSRF protection and URL normalization."""
import ipaddress
import re
import socket
from urllib.parse import urlparse, urlunparse, urljoin
from typing import Optional


# Private / reserved IP ranges to block
_BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Cloud metadata endpoints
_BLOCKED_HOSTS = {
    "metadata.google.internal",
    "169.254.169.254",
}


class SSRFError(Exception):
    pass


def validate_url(url: str) -> str:
    """
    Validate a URL for SSRF safety.
    Returns the normalized URL if safe, raises SSRFError otherwise.
    """
    parsed = urlparse(url)

    # Only allow http and https
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Scheme '{parsed.scheme}' not allowed. Only http/https.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname.")

    # Block known metadata endpoints
    if hostname in _BLOCKED_HOSTS:
        raise SSRFError(f"Access to '{hostname}' is blocked (metadata endpoint).")

    # Resolve hostname and check IP
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved:
            ip = ipaddress.ip_address(sockaddr[0])
            for blocked in _BLOCKED_RANGES:
                if ip in blocked:
                    raise SSRFError(f"Access to private/reserved IP '{ip}' is blocked.")
    except socket.gaierror:
        raise SSRFError(f"Cannot resolve hostname '{hostname}'.")

    return url


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize a URL: resolve relative, remove fragments, canonicalize trailing slashes."""
    if base_url and not url.startswith(("http://", "https://")):
        url = urljoin(base_url, url)

    parsed = urlparse(url)
    # Remove fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip("/") or "/",
        parsed.params,
        parsed.query,
        "",  # no fragment
    ))
    return normalized


def is_same_domain(url: str, base_url: str) -> bool:
    """Check if a URL belongs to the same domain as the base URL."""
    try:
        url_host = urlparse(url).hostname or ""
        base_host = urlparse(base_url).hostname or ""
        return url_host.lower() == base_host.lower()
    except Exception:
        return False


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    return urlparse(url).hostname or ""


# Smart exclude patterns
SMART_EXCLUDE_PATTERNS = {
    "privacy": "Privacy policy page",
    "terms": "Terms and conditions page",
    "cookie": "Cookie policy page",
    "login": "Login/authentication page",
    "account": "Account management page",
    "portal": "Resident/user portal",
    "apply": "Application form page",
    "resident": "Resident-only page",
    "admin": "Admin page",
    "sign-in": "Sign-in page",
    "sign-up": "Sign-up page",
    "register": "Registration page",
    "checkout": "Checkout page",
    "cart": "Shopping cart page",
}


def get_smart_exclude_suggestions(urls: list[str]) -> list[dict]:
    """Suggest URLs that should likely be excluded based on common patterns."""
    suggestions = []
    for url in urls:
        path = urlparse(url).path.lower()
        for pattern, reason in SMART_EXCLUDE_PATTERNS.items():
            if pattern in path:
                suggestions.append({
                    "url": url,
                    "reason": reason,
                    "pattern": pattern,
                })
                break
    return suggestions
