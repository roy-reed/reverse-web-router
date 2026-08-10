"""Cloud-boundary scanning and deterministic redaction."""
from __future__ import annotations

import re
from typing import Any, List

from .errors import SecurityError

SENSITIVE_KEY = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|secret|token|password|private[_-]?key|cookie|authorization)(?:$|[_-])",
    re.I,
)
WINDOWS_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
SECRET_TEXT = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
)


def is_sensitive_key(value: Any) -> bool:
    key = str(value)
    if SENSITIVE_KEY.search(key):
        return True
    compact = re.sub(r"[^A-Za-z0-9]", "", key).lower()
    if compact in {"apikey", "secret", "token", "password", "privatekey", "cookie", "authorization"}:
        return True
    return compact.endswith(("secret", "token", "password", "privatekey")) and not compact.endswith("tokens")


def scan_cloud_payload(value: Any, path: str = "$") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = "%s.%s" % (path, key)
            if is_sensitive_key(key) and child not in (None, "", False):
                findings.append("%s contains a sensitive field" % child_path)
            findings.extend(scan_cloud_payload(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_cloud_payload(child, "%s[%d]" % (path, index)))
    elif isinstance(value, str):
        if WINDOWS_ABSOLUTE.search(value):
            findings.append("%s contains a local absolute path" % path)
        for pattern in SECRET_TEXT:
            if pattern.search(value):
                findings.append("%s contains credential-like text" % path)
                break
    return findings


def ensure_cloud_safe(value: Any) -> None:
    findings = scan_cloud_payload(value)
    if findings:
        raise SecurityError(findings)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if is_sensitive_key(key) else redact(child))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        out = WINDOWS_ABSOLUTE.sub("[LOCAL_PATH]", value)
        for pattern in SECRET_TEXT:
            out = pattern.sub("[REDACTED]", out)
        return out
    return value


def redact_known_values(value: Any, secrets: List[str]) -> Any:
    """Remove exact runtime secret values even when they do not resemble a key."""
    secret_values = [item for item in secrets if item]
    if isinstance(value, dict):
        return {key: redact_known_values(child, secret_values) for key, child in value.items()}
    if isinstance(value, list):
        return [redact_known_values(item, secret_values) for item in value]
    if isinstance(value, str):
        out = value
        for secret in secret_values:
            out = out.replace(secret, "[REDACTED]")
        return out
    return value
