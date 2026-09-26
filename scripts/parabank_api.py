#!/usr/bin/env python3
"""Minimal ParaBank REST client shared by the data preparation and ledger scripts."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8080/parabank/services/bank"
SCRIPTABLE_ACCOUNT_TYPES = ("CHECKING", "SAVINGS")


def base_url():
    url = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise SystemExit("BASE_URL must be an HTTP(S) URL")
    return url


def _decode(body):
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"error": body}


def _request(path, params=None, method="GET", json_body=None, timeout=120):
    url = base_url() + path
    if params:
        url += "?" + urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Accept", "application/json")
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _decode(response.read().decode("utf-8", "replace").strip())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace").strip()
        raise SystemExit(f"{method} {path} failed with HTTP {error.code}: {detail or error.reason}") from error
    except urllib.error.URLError as error:
        raise SystemExit(f"{method} {path} could not reach ParaBank: {error.reason}") from error


def get(path, params=None):
    return _request(path, params)


def post(path, params=None, json_body=None, timeout=120):
    return _request(path, params, method="POST", json_body=json_body, timeout=timeout)


def login(username, password):
    return probe_get(f"/login/{urllib.parse.quote(username)}/{urllib.parse.quote(password)}")


def probe_get(path, params=None):
    """GET used for discovery: a missing resource yields None instead of aborting the preparation."""
    try:
        return get(path, params)
    except SystemExit:
        return None


def existing_customers(candidate_ids):
    return [customer_id for customer_id in candidate_ids if isinstance(probe_get(f"/customers/{customer_id}"), dict)]


def accounts_of(customer_id):
    listed = get(f"/customers/{customer_id}/accounts")
    if not isinstance(listed, list):
        return []
    return [account for account in listed if account.get("type") in SCRIPTABLE_ACCOUNT_TYPES]


def entries_of(account_id):
    listed = get(f"/accounts/{account_id}/transactions")
    return listed if isinstance(listed, list) else []


def env_int(name, fallback):
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return fallback
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"{name} must be an integer, got {raw!r}")
    if value <= 0:
        raise SystemExit(f"{name} must be positive, got {value}")
    return value
