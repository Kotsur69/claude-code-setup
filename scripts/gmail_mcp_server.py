"""
Gmail MCP stdio server for Claude Code.
Same pattern as google_calendar_mcp_server.py — bypasses remote HTTP OAuth issues.
First run: opens browser for Google OAuth consent.
Subsequent runs: uses saved token.

Add to Claude Code (or use the checked-in .mcp.json, which already points here):
  claude mcp add --scope user gmail -- python3 ${CLAUDE_PROJECT_DIR}/scripts/gmail_mcp_server.py
"""
import json
import os
import sys
import traceback

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(
    _SCRIPT_DIR, "client_secret_2_93926080486-9isn8ejmtt6p7a96ihs1tt6du5u2offl.apps.googleusercontent.com.json"
)
TOKEN_FILE = os.path.expanduser("~/.claude/gmail_token.json")
SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
]
CALLBACK_PORT = 8086


def get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=CALLBACK_PORT, open_browser=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def get_service():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=get_credentials())


def _format_message(msg):
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "labelIds": msg.get("labelIds", []),
    }


def search_messages(args):
    svc = get_service()
    query = args.get("query", "")
    max_results = min(args.get("max_results", 20), 50)
    include_spam_trash = args.get("include_spam_trash", False)

    result = svc.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
        includeSpamTrash=include_spam_trash,
    ).execute()

    messages = result.get("messages", [])
    if not messages:
        return []

    out = []
    for m in messages:
        full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                          metadataHeaders=["Subject", "From", "To", "Date"]).execute()
        out.append(_format_message(full))
    return out


def get_message(args):
    svc = get_service()
    msg_id = args["message_id"]
    fmt = args.get("format", "full")
    msg = svc.users().messages().get(userId="me", id=msg_id, format=fmt).execute()

    if fmt == "full":
        parts = msg.get("payload", {}).get("parts", [])
        body = ""
        for part in parts:
            if part.get("mimeType") == "text/plain":
                import base64
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    break
        result = _format_message(msg)
        result["body"] = body
        return result

    return _format_message(msg)


def trash_message(args):
    svc = get_service()
    msg_id = args["message_id"]
    svc.users().messages().trash(userId="me", id=msg_id).execute()
    return {"trashed": True, "message_id": msg_id}


def delete_message(args):
    svc = get_service()
    msg_id = args["message_id"]
    svc.users().messages().delete(userId="me", id=msg_id).execute()
    return {"deleted": True, "message_id": msg_id}


def batch_trash(args):
    svc = get_service()
    ids = args["message_ids"]
    svc.users().messages().batchModify(
        userId="me",
        body={"ids": ids, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX", "SPAM"]},
    ).execute()
    return {"trashed": len(ids), "message_ids": ids}


def batch_delete(args):
    svc = get_service()
    ids = args["message_ids"]
    svc.users().messages().batchDelete(userId="me", body={"ids": ids}).execute()
    return {"deleted": len(ids), "message_ids": ids}


def list_labels(args):
    svc = get_service()
    result = svc.users().labels().list(userId="me").execute()
    return [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in result.get("labels", [])]


def mark_read(args):
    svc = get_service()
    ids = args["message_ids"]
    svc.users().messages().batchModify(
        userId="me",
        body={"ids": ids, "removeLabelIds": ["UNREAD"]},
    ).execute()
    return {"marked_read": len(ids)}


TOOLS = {
    "search_messages": {
        "fn": search_messages,
        "description": "Search Gmail messages. Supports Gmail query syntax (e.g. 'in:spam', 'is:unread', 'from:example.com', 'newer_than:1d').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query (e.g. 'in:spam newer_than:1d', 'is:unread from:noreply')"},
                "max_results": {"type": "integer", "description": "Max messages to return (default: 20, max: 50)"},
                "include_spam_trash": {"type": "boolean", "description": "Include spam and trash in results (default: false)"},
            },
        },
    },
    "get_message": {
        "fn": get_message,
        "description": "Get full content of a Gmail message by ID.",
        "inputSchema": {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {"type": "string"},
                "format": {"type": "string", "description": "'full' (default) or 'metadata'"},
            },
        },
    },
    "trash_message": {
        "fn": trash_message,
        "description": "Move a single message to Trash.",
        "inputSchema": {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {"type": "string"},
            },
        },
    },
    "delete_message": {
        "fn": delete_message,
        "description": "Permanently delete a single message (cannot be undone).",
        "inputSchema": {
            "type": "object",
            "required": ["message_id"],
            "properties": {
                "message_id": {"type": "string"},
            },
        },
    },
    "batch_trash": {
        "fn": batch_trash,
        "description": "Move multiple messages to Trash at once.",
        "inputSchema": {
            "type": "object",
            "required": ["message_ids"],
            "properties": {
                "message_ids": {"type": "array", "items": {"type": "string"}, "description": "List of message IDs to trash"},
            },
        },
    },
    "batch_delete": {
        "fn": batch_delete,
        "description": "Permanently delete multiple messages at once (cannot be undone).",
        "inputSchema": {
            "type": "object",
            "required": ["message_ids"],
            "properties": {
                "message_ids": {"type": "array", "items": {"type": "string"}, "description": "List of message IDs to permanently delete"},
            },
        },
    },
    "list_labels": {
        "fn": list_labels,
        "description": "List all Gmail labels (system and user-defined).",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "mark_read": {
        "fn": mark_read,
        "description": "Mark multiple messages as read.",
        "inputSchema": {
            "type": "object",
            "required": ["message_ids"],
            "properties": {
                "message_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


def send(msg):
    data = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def handle(req):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "gmail", "version": "1.0.0"},
            }
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        tools = [{"name": n, "description": t["description"], "inputSchema": t["inputSchema"]} for n, t in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        if tool_name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}
        try:
            result = TOOLS[tool_name]["fn"](args)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            }
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e), "data": traceback.format_exc()}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    try:
        get_credentials()
    except Exception as e:
        sys.stderr.write(f"Auth error: {e}\n")
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(req)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
