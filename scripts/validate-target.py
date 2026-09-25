#!/usr/bin/env python3
import os
import socket
import ipaddress
import sys
from urllib.parse import urlparse

raw = os.environ.get("BASE_URL", "")
if not raw:
    sys.exit("BASE_URL must be configured in the isolated GitHub environment")
try:
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
except ValueError as exc:
    sys.exit(f"Invalid BASE_URL: {exc}")
allowed = {value.strip().lower() for value in os.environ.get("ALLOWED_HOSTS", "").split(",") if value.strip()}
if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password or parsed.query or parsed.fragment:
    sys.exit("BASE_URL must be an HTTP(S) URL without embedded credentials, query, or fragment")
if host == "parabank.parasoft.com":
    sys.exit("The public ParaBank site is never an allowed performance target")
try:
    addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))}
except (OSError, ValueError) as exc:
    sys.exit(f"Could not resolve isolated target: {exc}")
if not addresses or not all(address.is_private or address.is_loopback or address.is_link_local for address in addresses):
    sys.exit("Refusing target: every resolved address must be private, loopback, or link-local")
if host not in {"localhost", "127.0.0.1", "::1"} and host not in allowed:
    sys.exit("Refusing target: non-local host is not listed in ALLOWED_HOSTS")
print("Target accepted for the isolated performance environment")
