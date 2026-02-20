#!/usr/bin/env python3
"""ecom_client - CLI client for ecom_agent backend API

Usage:
    python ecom_client.py health
    python ecom_client.py flow list
    python ecom_client.py flow get <flow_id>
    python ecom_client.py task list [--status <status>]
    python ecom_client.py task create --flow <id> --name <name> --params <json>
    python ecom_client.py task get <task_id>
    python ecom_client.py task delete <task_id>
    python ecom_client.py storage list

Environment:
    ECOM_SERVER_URL  Server base URL (default: http://192.168.3.100:8088)
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

SERVER_URL = os.environ.get("ECOM_SERVER_URL", "http://192.168.3.100:8088")
API_PREFIX = "/api"


def _request(method, path, body=None):
    url = f"{SERVER_URL}{API_PREFIX}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = opener.open(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            return {"error": True, "status": e.code, "detail": json.loads(err).get("detail", err)}
        except json.JSONDecodeError:
            return {"error": True, "status": e.code, "detail": err}
    except urllib.error.URLError as e:
        return {"error": True, "detail": f"Connection failed: {e.reason}"}


def _out(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ── Commands ──────────────────────────────────────────

def cmd_health(_a):
    _out(_request("GET", "/health"))

def cmd_flow_list(_a):
    _out(_request("GET", "/flows"))

def cmd_flow_get(a):
    _out(_request("GET", f"/flows/{a.flow_id}"))

def cmd_flow_reload(_a):
    _out(_request("POST", "/flows/reload"))

def cmd_task_list(a):
    path = f"/tasks?status={a.status}" if a.status else "/tasks"
    _out(_request("GET", path))

def cmd_task_create(a):
    _out(_request("POST", "/tasks", {
        "flow_id": a.flow,
        "name": a.name,
        "parameters": json.loads(a.params) if a.params else {},
        "schedule_type": a.schedule,
    }))

def cmd_task_get(a):
    _out(_request("GET", f"/tasks/{a.task_id}"))

def cmd_task_delete(a):
    _out(_request("DELETE", f"/tasks/{a.task_id}"))

def cmd_storage_list(_a):
    _out(_request("GET", "/storage"))


# ── CLI ───────────────────────────────────────────────

def main():
    global SERVER_URL
    p = argparse.ArgumentParser(description="ecom_agent CLI client")
    p.add_argument("--server", help=f"Server URL (default: {SERVER_URL})")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("health")

    fp = sub.add_parser("flow")
    fs = fp.add_subparsers(dest="action")
    fs.add_parser("list")
    fg = fs.add_parser("get"); fg.add_argument("flow_id")
    fs.add_parser("reload")

    tp = sub.add_parser("task")
    ts = tp.add_subparsers(dest="action")
    tl = ts.add_parser("list")
    tl.add_argument("--status", choices=["pending", "running", "waiting", "completed", "failed"])
    tc = ts.add_parser("create")
    tc.add_argument("--flow", required=True)
    tc.add_argument("--name", required=True)
    tc.add_argument("--params", default="{}")
    tc.add_argument("--schedule", default="immediate", choices=["immediate", "periodic"])
    tg = ts.add_parser("get"); tg.add_argument("task_id", type=int)
    td = ts.add_parser("delete"); td.add_argument("task_id", type=int)

    sp = sub.add_parser("storage")
    ss = sp.add_subparsers(dest="action")
    ss.add_parser("list")

    args = p.parse_args()
    if args.server:
        SERVER_URL = args.server.rstrip("/")

    dispatch = {
        ("health", None): cmd_health,
        ("flow", "list"): cmd_flow_list,
        ("flow", "get"): cmd_flow_get,
        ("flow", "reload"): cmd_flow_reload,
        ("task", "list"): cmd_task_list,
        ("task", "create"): cmd_task_create,
        ("task", "get"): cmd_task_get,
        ("task", "delete"): cmd_task_delete,
        ("storage", "list"): cmd_storage_list,
    }

    handler = dispatch.get((args.command, getattr(args, "action", None)))
    if handler:
        handler(args)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
