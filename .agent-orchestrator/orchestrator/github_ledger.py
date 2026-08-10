"""Durable GitHub Issue ledger for claims, paid boundaries and task status."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

from .errors import ClaimConflictError, DuplicatePaidInvocationError
from .security import ensure_cloud_safe, redact
from .state import TASK_STATES
from .yamlmini import parse as parse_yaml

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FENCE_RE = re.compile(r"```(json|ya?ml)\s*\n(.*?)\n```", re.I | re.S)
LEDGER_RE = re.compile(r"<!-- rwrouter-ledger:([^\n]+)\n(\{.*?\})\n-->", re.S)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_identity(repo: str, task_id: str) -> None:
    if not REPO_RE.fullmatch(repo):
        raise ValueError("invalid GitHub repository identifier")
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("unsafe task_id")


def render_ledger(record: Dict[str, Any]) -> str:
    safe = redact(record)
    ensure_cloud_safe(safe)
    task_id = str(safe["task_id"])
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("unsafe task_id")
    compact = json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    summary = str(safe.get("summary") or "No summary yet.")
    return (
        "<!-- rwrouter-ledger:%s\n%s\n-->\n\n"
        "**Agent task:** `%s`  \n**Canonical state:** `%s`\n\n%s\n"
        % (task_id, compact, task_id, safe["state"], summary)
    )


def parse_ledger(body: str) -> Optional[Dict[str, Any]]:
    match = LEDGER_RE.search(body or "")
    if not match:
        return None
    task_id, raw = match.groups()
    record = json.loads(raw)
    if record.get("task_id") != task_id:
        raise ValueError("ledger marker and record task_id differ")
    if record.get("state") not in TASK_STATES:
        raise ValueError("ledger contains an unknown canonical state")
    return record


def find_ledger(comments: Iterable[Dict[str, Any]], task_id: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
    matches = []
    for comment in comments:
        record = parse_ledger(str(comment.get("body") or ""))
        if record and record.get("task_id") == task_id:
            matches.append((int(comment["id"]), record))
    if len(matches) > 1:
        raise ClaimConflictError("multiple canonical ledger comments exist for %s" % task_id)
    return matches[0] if matches else (None, None)


def prepare_claim(existing: Optional[Dict[str, Any]], task_id: str, worker: str) -> Tuple[Dict[str, Any], bool]:
    if existing is None:
        return ({
            "schema": "agent-ledger/v1",
            "task_id": task_id,
            "worker": worker,
            "state": "claimed",
            "paid_invoked": False,
            "provider_run_id": None,
            "claimed_at": _now(),
            "updated_at": _now(),
            "summary": "Task contract claimed; provider invocation has not started.",
        }, True)
    if existing.get("worker") != worker:
        raise ClaimConflictError("task %s is already claimed by %s" % (task_id, existing.get("worker")))
    if existing.get("paid_invoked"):
        return existing, False
    if existing.get("state") not in ("ready", "queued", "claimed"):
        return existing, False
    record = dict(existing)
    record["state"] = "claimed"
    record["updated_at"] = _now()
    return record, True


def prepare_paid(record: Dict[str, Any], provider_run_id: str) -> Dict[str, Any]:
    if record.get("paid_invoked"):
        raise DuplicatePaidInvocationError("paid invocation already recorded for %s" % record.get("task_id"))
    if record.get("state") != "claimed":
        raise ClaimConflictError("paid invocation requires claimed state")
    updated = dict(record)
    updated.update({
        "paid_invoked": True,
        "provider_run_id": provider_run_id,
        "state": "running",
        "invoked_at": _now(),
        "updated_at": _now(),
        "summary": "Paid invocation boundary recorded before the provider request.",
    })
    return updated


def prepare_state(record: Dict[str, Any], state: str, summary: str = "") -> Dict[str, Any]:
    if state not in TASK_STATES:
        raise ValueError("unknown canonical task state %r" % state)
    updated = dict(record)
    updated["state"] = state
    updated["updated_at"] = _now()
    if summary:
        updated["summary"] = summary
    return updated


def prepare_result(record: Dict[str, Any], worker_result: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(record)
    result = worker_result.get("result")
    errors = worker_result.get("errors") or []
    if result and not errors:
        updated["state"] = "verifying"
        updated["provider_run_id"] = result.get("provider_run_id") or updated.get("provider_run_id")
        updated["summary"] = result.get("summary") or "Worker completed; deterministic verification is pending."
    else:
        updated["state"] = "failed"
        updated["summary"] = "; ".join(str(item) for item in errors)[:2000] or "Worker failed without a result."
    updated["updated_at"] = _now()
    return updated


def extract_task_contract(body: str) -> Optional[Dict[str, Any]]:
    matches = FENCE_RE.findall(body or "")
    for language, raw in matches:
        try:
            parsed = json.loads(raw) if language.lower() == "json" else parse_yaml(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict) and parsed.get("schema") == "agent-task/v1":
            return parsed
    return None


class GitHubClient:
    """Small REST client; the token is used only in the Authorization header."""

    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.api_url + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "User-Agent": "reverse-web-router/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError("GitHub API request failed with HTTP %d" % exc.code) from None
        return json.loads(raw.decode("utf-8")) if raw else None

    def comments(self, repo: str, issue: int) -> list[Dict[str, Any]]:
        comments: list[Dict[str, Any]] = []
        for page in range(1, 101):
            batch = self.request(
                "GET",
                "/repos/%s/issues/%d/comments?per_page=100&page=%d" % (repo, issue, page),
            )
            comments.extend(batch)
            if len(batch) < 100:
                return comments
        raise RuntimeError("Issue comment pagination exceeded the fail-closed limit")

    def write_ledger(self, repo: str, issue: int, comment_id: Optional[int], record: Dict[str, Any]) -> int:
        body = render_ledger(record)
        if comment_id is None:
            response = self.request("POST", "/repos/%s/issues/%d/comments" % (repo, issue), {"body": body})
        else:
            response = self.request("PATCH", "/repos/%s/issues/comments/%d" % (repo, comment_id), {"body": body})
        return int(response["id"])

    def ledger(self, repo: str, issue: int, task_id: str) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        _validate_identity(repo, task_id)
        return find_ledger(self.comments(repo, issue), task_id)

    def find_task_issue(self, repo: str, task_id: str) -> Optional[int]:
        _validate_identity(repo, task_id)
        matches = []
        for page in range(1, 11):
            query = urllib.parse.urlencode({
                "q": 'repo:%s type:issue in:body "%s"' % (repo, task_id),
                "per_page": 100,
                "page": page,
            })
            response = self.request("GET", "/search/issues?" + query)
            items = response.get("items") or []
            for item in items:
                contract = extract_task_contract(str(item.get("body") or ""))
                if contract and contract.get("task_id") == task_id:
                    matches.append(int(item["number"]))
            if len(items) < 100:
                break
        else:
            raise RuntimeError("GitHub task search exceeded the fail-closed limit")
        if len(matches) > 1:
            raise ClaimConflictError("multiple Issues declare task_id %s" % task_id)
        return matches[0] if matches else None

    def dependency_states(self, repo: str, depends_on: Iterable[str]) -> Dict[str, str]:
        states: Dict[str, str] = {}
        for task_id in depends_on:
            issue = self.find_task_issue(repo, task_id)
            if issue is None:
                continue
            _, record = self.ledger(repo, issue, task_id)
            if record:
                states[task_id] = str(record["state"])
        return states
