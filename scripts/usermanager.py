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
    os.path.join(os.path.expanduser("~"), ".config", "kernelci", "usermanager.toml"),
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


def _parse_group_list(values):
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    groups = []
    for value in values:
        for group in value.split(","):
            group = group.strip()
            if group:
                groups.append(group)
    return groups


def _dedupe(items):
    seen = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _extract_group_names(payload):
    groups = payload.get("groups") or []
    names = []
    for group in groups:
        if isinstance(group, dict):
            name = group.get("name")
        else:
            name = getattr(group, "name", None)
        if name:
            names.append(name)
    return _dedupe(names)


def _apply_group_changes(current, add_groups, remove_groups):
    current = _dedupe(current)
    remove_set = set(remove_groups)
    updated = [group for group in current if group not in remove_set]
    for group in add_groups:
        if group not in updated and group not in remove_set:
            updated.append(group)
    return updated


def _resolve_user_id(user_id, api_url, token):
    if "@" not in user_id:
        return user_id
    status, body = _request_json("GET", f"{api_url}/users", token=token)
    if status >= 400:
        _print_response(status, body)
        raise SystemExit(1)
    try:
        payload = json.loads(body) if body else []
    except json.JSONDecodeError as exc:
        raise SystemExit("Failed to parse users response") from exc
    if not isinstance(payload, list):
        raise SystemExit("Unexpected users response")
    matches = [
        user
        for user in payload
        if isinstance(user, dict) and user.get("email") == user_id
    ]
    if not matches:
        raise SystemExit(f"No user found with email: {user_id}")
    if len(matches) > 1:
        raise SystemExit(f"Multiple users found with email: {user_id}")
    resolved_id = matches[0].get("id")
    if not resolved_id:
        raise SystemExit(f"User with email {user_id} has no id")
    return resolved_id


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
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
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
            "  ./scripts/usermanager.py print-config-example\n"
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
    parser.add_argument(
        "--api-url", help="API base URL, e.g. " "http://localhost:8001/latest"
    )
    parser.add_argument("--token", help="Bearer token for admin/user actions")
    parser.add_argument("--instance", help="Instance name from config")
    parser.add_argument(
        "--token-label", default="Auth", help="Label used when prompting for a token"
    )

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

    invite_url = subparsers.add_parser("invite-url", help="Preview invite URL base")

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

    update_user = subparsers.add_parser("update-user", help="Patch user by id")
    update_user.add_argument("user_id")
    update_user.add_argument("--data", help="JSON object with fields to update")
    update_user.add_argument("--username", help="Set username")
    update_user.add_argument("--email", help="Set email")
    update_user.add_argument("--password", help="Set password")
    update_user.add_argument(
        "--superuser", dest="is_superuser", action="store_true", help="Grant superuser"
    )
    update_user.add_argument(
        "--no-superuser",
        dest="is_superuser",
        action="store_false",
        help="Revoke superuser",
    )
    update_user.add_argument(
        "--active", dest="is_active", action="store_true", help="Set is_active true"
    )
    update_user.add_argument(
        "--inactive", dest="is_active", action="store_false", help="Set is_active false"
    )
    update_user.add_argument(
        "--verified",
        dest="is_verified",
        action="store_true",
        help="Set is_verified true",
    )
    update_user.add_argument(
        "--unverified",
        dest="is_verified",
        action="store_false",
        help="Set is_verified false",
    )
    update_user.set_defaults(is_active=None, is_verified=None, is_superuser=None)
    update_user.add_argument(
        "--set-groups",
        help="Replace all groups with a comma-separated list",
    )
    update_user.add_argument(
        "--add-group",
        action="append",
        default=[],
        help="Add group(s); can be used multiple times or with commas",
    )
    update_user.add_argument(
        "--remove-group",
        action="append",
        default=[],
        help="Remove group(s); can be used multiple times or with commas",
    )

    delete_user = subparsers.add_parser("delete-user", help="Delete user by id")
    delete_user.add_argument("user_id")

    subparsers.add_parser(
        "print-config-example", help="Print a sample usermanager.toml"
    )

    args = parser.parse_args()

    if args.command == "print-config-example":
        print(
            'default_instance = "local"\n\n'
            "[instances.local]\n"
            'url = "http://localhost:8001/latest"\n'
            'token = "<admin-or-user-token>"\n\n'
            "[instances.staging]\n"
            'url = "https://staging.kernelci.org:9000/latest"\n'
            'token = "<admin-or-user-token>"\n'
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

    if args.command in {
        "invite",
        "invite-url",
        "whoami",
        "list-users",
        "get-user",
        "update-user",
        "delete-user",
    }:
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
        status, body = _request_json("GET", f"{api_url}/user/invite/url", token=token)
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
        status, body = _request_json("POST", f"{api_url}/user/accept-invite", payload)
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
        resolved_id = _resolve_user_id(args.user_id, api_url, token)
        status, body = _request_json(
            "GET", f"{api_url}/user/{resolved_id}", token=token
        )
    elif args.command == "update-user":
        resolved_id = _resolve_user_id(args.user_id, api_url, token)
        data = {}
        if args.data:
            try:
                data = json.loads(args.data)
            except json.JSONDecodeError as exc:
                raise SystemExit("Invalid JSON for --data") from exc
            if not isinstance(data, dict):
                raise SystemExit("--data must be a JSON object")
        if args.username:
            data["username"] = args.username
        if args.email:
            data["email"] = args.email
        if args.password:
            data["password"] = args.password
        if args.is_superuser is not None:
            data["is_superuser"] = args.is_superuser
        if args.is_active is not None:
            data["is_active"] = args.is_active
        if args.is_verified is not None:
            data["is_verified"] = args.is_verified

        set_groups = _parse_group_list(args.set_groups)
        add_groups = _parse_group_list(args.add_group)
        remove_groups = _parse_group_list(args.remove_group)
        if set_groups or add_groups or remove_groups:
            if set_groups:
                current_groups = set_groups
            else:
                status, body = _request_json(
                    "GET", f"{api_url}/user/{resolved_id}", token=token
                )
                if status >= 400:
                    _print_response(status, body)
                    raise SystemExit(1)
                try:
                    payload = json.loads(body) if body else {}
                except json.JSONDecodeError as exc:
                    raise SystemExit("Failed to parse user response") from exc
                current_groups = _extract_group_names(payload)
            data["groups"] = _apply_group_changes(
                current_groups, add_groups, remove_groups
            )

        if not data:
            raise SystemExit("No updates specified. Use --data or flags.")
        status, body = _request_json(
            "PATCH", f"{api_url}/user/{resolved_id}", data, token=token
        )
    elif args.command == "delete-user":
        resolved_id = _resolve_user_id(args.user_id, api_url, token)
        status, body = _request_json(
            "DELETE", f"{api_url}/user/{resolved_id}", token=token
        )
    else:
        raise SystemExit("Unknown command")

    _print_response(status, body)
    if status >= 400:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
