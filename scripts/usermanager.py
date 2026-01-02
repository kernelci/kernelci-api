#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    import tomllib
except ImportError as exc:  # pragma: no cover - Python < 3.11
    raise SystemExit("Python 3.11+ is required for tomllib.") from exc


DEFAULT_CONFIG_PATHS = [
    os.path.join(os.getcwd(), "usermanager.toml"),
    os.path.join(os.path.expanduser("~"), ".config", "kernelci",
                 "usermanager.toml"),
]


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def _resolve_config_path(path: str | None) -> str | None:
    if path:
        return path
    for candidate in DEFAULT_CONFIG_PATHS:
        if os.path.exists(candidate):
            return candidate
    return None


def _get_setting(args_value, env_key, config, config_key):
    if args_value:
        return args_value
    env_value = os.getenv(env_key)
    if env_value:
        return env_value
    current = config
    for key in config_key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _get_instance_config(config, instance_name):
    if not isinstance(config, dict):
        return {}
    instances = config.get("instances", {})
    if not isinstance(instances, dict):
        return {}
    return instances.get(instance_name, {}) or {}


def _prompt_if_missing(value, prompt_text, secret=False, default=None):
    if value:
        return value
    if secret:
        return getpass.getpass(prompt_text)
    prompt = prompt_text
    if default:
        prompt = f"{prompt_text} [{default}] "
    response = input(prompt)
    if not response and default is not None:
        return default
    return response


def _request_json(method, url, data=None, token=None, form=False):
    headers = {"accept": "application/json"}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req) as response:
            payload = response.read().decode("utf-8")
            return response.status, payload
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, payload


def _print_response(status, payload):
    try:
        parsed = json.loads(payload) if payload else None
    except json.JSONDecodeError:
        parsed = None
    if parsed is not None:
        print(json.dumps(parsed, indent=2))
    elif payload:
        print(payload)
    else:
        print(f"Status: {status}")


def _require_token(token, args):
    return _prompt_if_missing(
        token,
        f"{args.token_label} token: ",
        secret=True,
    )


def main():
    default_paths = "\n".join(f"  - {path}" for path in DEFAULT_CONFIG_PATHS)
    parser = argparse.ArgumentParser(
        description="KernelCI API user management helper",
        epilog=(
            "Examples:\n"
            "  ./scripts/usermanager.py invite --username alice --email "
            "alice@example.org --return-token\n"
            "  ./scripts/usermanager.py accept-invite --token <INVITE-TOKEN>\n"
            "  ./scripts/usermanager.py login --username alice\n"
            "  ./scripts/usermanager.py whoami\n"
            "  ./scripts/usermanager.py list-users --instance staging\n"
            "  ./scripts/usermanager.py print-config\n"
            "\n"
            "Default config lookup (first match wins):\n"
            f"{default_paths}\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        help="Path to usermanager.toml (defaults to first match in the lookup list below)",
    )
    parser.add_argument("--api-url", help="API base URL, e.g. "
                                          "http://localhost:8001/latest")
    parser.add_argument("--token", help="Bearer token for admin/user actions")
    parser.add_argument("--instance", help="Instance name from config")
    parser.add_argument("--token-label", default="Auth",
                        help="Label used when prompting for a token")

    subparsers = parser.add_subparsers(dest="command", required=True)

    invite = subparsers.add_parser("invite", help="Invite a new user")
    invite.add_argument("--username", required=True)
    invite.add_argument("--email", required=True)
    invite.add_argument("--groups", default="")
    invite.add_argument("--superuser", action="store_true")
    invite.add_argument("--send-email", action="store_true", default=True)
    invite.add_argument("--no-send-email", action="store_true")
    invite.add_argument("--return-token", action="store_true")
    invite.add_argument("--resend-if-exists", action="store_true")

    invite_url = subparsers.add_parser("invite-url",
                                       help="Preview invite URL base")

    accept = subparsers.add_parser("accept-invite", help="Accept an invite")
    accept.add_argument("--token")
    accept.add_argument("--password")

    login = subparsers.add_parser("login", help="Get an auth token")
    login.add_argument("--username", required=True)
    login.add_argument("--password")

    whoami = subparsers.add_parser("whoami", help="Show current user")

    list_users = subparsers.add_parser("list-users", help="List users")

    get_user = subparsers.add_parser("get-user", help="Get user by id")
    get_user.add_argument("user_id")

    update_user = subparsers.add_parser("update-user",
                                        help="Patch user by id")
    update_user.add_argument("user_id")
    update_user.add_argument("--data", required=True,
                             help="JSON object with fields to update")

    delete_user = subparsers.add_parser("delete-user",
                                        help="Delete user by id")
    delete_user.add_argument("user_id")

    subparsers.add_parser("print-config",
                          help="Print a sample usermanager.toml")

    args = parser.parse_args()

    if args.command == "print-config":
        print(
            "default_instance = \"local\"\n\n"
            "[instances.local]\n"
            "url = \"http://localhost:8001/latest\"\n"
            "token = \"<admin-or-user-token>\"\n\n"
            "[instances.staging]\n"
            "url = \"https://staging.kernelci.org/latest\"\n"
            "token = \"<admin-or-user-token>\"\n"
        )
        return

    config_path = _resolve_config_path(args.config)
    config = _load_config(config_path)
    instance_name = (
        args.instance
        or os.getenv("KCI_API_INSTANCE")
        or config.get("default_instance")
        or "default"
    )
    instance_config = _get_instance_config(config, instance_name)

    api_url = args.api_url or os.getenv("KCI_API_URL")
    if not api_url:
        api_url = instance_config.get("url")
    if not api_url:
        api_url = _get_setting(None, "KCI_API_URL", config, "api.url")
    api_url = _prompt_if_missing(
        api_url,
        "API URL",
        default="http://localhost:8001/latest",
    ).rstrip("/")

    token = args.token or os.getenv("KCI_API_TOKEN")
    if not token:
        token = instance_config.get("token")
    if not token:
        token = _get_setting(None, "KCI_API_TOKEN", config, "api.token")

    if args.command in {"invite", "invite-url", "whoami", "list-users",
                        "get-user", "update-user", "delete-user"}:
        token = _require_token(token, args)

    if args.command == "invite":
        groups = [g for g in args.groups.split(",") if g]
        payload = {
            "username": args.username,
            "email": args.email,
            "groups": groups,
            "is_superuser": args.superuser,
            "send_email": False if args.no_send_email else args.send_email,
            "return_token": args.return_token,
            "resend_if_exists": args.resend_if_exists,
        }
        status, body = _request_json(
            "POST", f"{api_url}/user/invite", payload, token=token
        )
    elif args.command == "invite-url":
        status, body = _request_json(
            "GET", f"{api_url}/user/invite/url", token=token
        )
    elif args.command == "accept-invite":
        invite_token = _prompt_if_missing(
            args.token,
            "Invite token: ",
            secret=True,
        )
        password = _prompt_if_missing(
            args.password,
            "New password: ",
            secret=True,
        )
        payload = {"token": invite_token, "password": password}
        status, body = _request_json(
            "POST", f"{api_url}/user/accept-invite", payload
        )
    elif args.command == "login":
        password = _prompt_if_missing(
            args.password,
            "Password: ",
            secret=True,
        )
        payload = {"username": args.username, "password": password}
        status, body = _request_json(
            "POST",
            f"{api_url}/user/login",
            payload,
            form=True,
        )
    elif args.command == "whoami":
        status, body = _request_json("GET", f"{api_url}/whoami", token=token)
    elif args.command == "list-users":
        status, body = _request_json("GET", f"{api_url}/users", token=token)
    elif args.command == "get-user":
        status, body = _request_json(
            "GET", f"{api_url}/user/{args.user_id}", token=token
        )
    elif args.command == "update-user":
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as exc:
            raise SystemExit("Invalid JSON for --data") from exc
        status, body = _request_json(
            "PATCH", f"{api_url}/user/{args.user_id}", data, token=token
        )
    elif args.command == "delete-user":
        status, body = _request_json(
            "DELETE", f"{api_url}/user/{args.user_id}", token=token
        )
    else:
        raise SystemExit("Unknown command")

    _print_response(status, body)
    if status >= 400:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
