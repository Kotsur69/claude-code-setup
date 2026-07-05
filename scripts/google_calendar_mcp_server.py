"""
Google Calendar MCP stdio server for Claude Code.
Bypasses the remote MCP DCR bug entirely.
First run: opens browser for Google OAuth consent.
Subsequent runs: uses saved token.

Add to Claude Code (or use the checked-in .mcp.json, which already points here):
  claude mcp add --scope user google-calendar -- python3 ${CLAUDE_PROJECT_DIR}/scripts/google_calendar_mcp_server.py
"""
import json
import os
import sys
import traceback
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(
    _SCRIPT_DIR, "client_secret_2_93926080486-9isn8ejmtt6p7a96ihs1tt6du5u2offl.apps.googleusercontent.com.json"
)
TOKEN_FILE = os.path.expanduser("~/.claude/google_calendar_token.json")
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]
CALLBACK_PORT = 8085


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
    return build("calendar", "v3", credentials=get_credentials())


def list_calendars(args):
    svc = get_service()
    result = svc.calendarList().list().execute()
    calendars = result.get("items", [])
    return [{"id": c["id"], "summary": c.get("summary", ""), "primary": c.get("primary", False)} for c in calendars]


def list_events(args):
    svc = get_service()
    calendar_id = args.get("calendar_id", "primary")
    max_results = args.get("max_results", 10)
    time_min = args.get("time_min", datetime.now(timezone.utc).isoformat())
    time_max = args.get("time_max")

    params = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
        "timeMin": time_min,
    }
    if time_max:
        params["timeMax"] = time_max

    result = svc.events().list(**params).execute()
    events = result.get("items", [])
    return [
        {
            "id": e["id"],
            "summary": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date")),
            "end": e["end"].get("dateTime", e["end"].get("date")),
            "location": e.get("location"),
            "description": e.get("description"),
            "htmlLink": e.get("htmlLink"),
        }
        for e in events
    ]


def create_calendar(args):
    svc = get_service()
    summary = args["summary"]
    color_id = args.get("color_id")
    body = {"summary": summary}
    cal = svc.calendars().insert(body=body).execute()
    cal_id = cal["id"]
    if color_id:
        svc.calendarList().patch(calendarId=cal_id, body={"colorId": color_id}).execute()
    return {"id": cal_id, "summary": summary}


def create_event(args):
    svc = get_service()
    calendar_id = args.get("calendar_id", "primary")
    event = {
        "summary": args["summary"],
        "start": args["start"],
        "end": args["end"],
    }
    if "location" in args:
        event["location"] = args["location"]
    if "description" in args:
        event["description"] = args["description"]
    if "attendees" in args:
        event["attendees"] = [{"email": e} for e in args["attendees"]]
    if "reminders" in args:
        event["reminders"] = args["reminders"]
    else:
        event["reminders"] = {"useDefault": True}
    result = svc.events().insert(calendarId=calendar_id, body=event).execute()
    return {"id": result["id"], "htmlLink": result.get("htmlLink"), "summary": result.get("summary")}


def update_event(args):
    svc = get_service()
    calendar_id = args.get("calendar_id", "primary")
    event_id = args["event_id"]
    existing = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    for field in ["summary", "start", "end", "location", "description"]:
        if field in args:
            existing[field] = args[field]
    result = svc.events().update(calendarId=calendar_id, eventId=event_id, body=existing).execute()
    return {"id": result["id"], "summary": result.get("summary"), "htmlLink": result.get("htmlLink")}


def delete_event(args):
    svc = get_service()
    calendar_id = args.get("calendar_id", "primary")
    event_id = args["event_id"]
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"deleted": True, "event_id": event_id}


TOOLS = {
    "create_calendar": {
        "fn": create_calendar,
        "description": "Create a new Google Calendar with optional color",
        "inputSchema": {
            "type": "object",
            "required": ["summary"],
            "properties": {
                "summary": {"type": "string", "description": "Calendar name"},
                "color_id": {"type": "string", "description": "Color: 1=lavender,2=sage,3=grape,4=flamingo,5=banana,6=tangerine,7=peacock,8=graphite,9=blueberry,10=basil,11=tomato"},
            },
        },
    },
    "list_calendars": {
        "fn": list_calendars,
        "description": "List all Google Calendars for the user",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "list_events": {
        "fn": list_events,
        "description": "List upcoming calendar events",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                "max_results": {"type": "integer", "description": "Max number of events to return (default: 10)"},
                "time_min": {"type": "string", "description": "Start time ISO8601 (default: now)"},
                "time_max": {"type": "string", "description": "End time ISO8601 (optional)"},
            },
        },
    },
    "create_event": {
        "fn": create_event,
        "description": "Create a new calendar event",
        "inputSchema": {
            "type": "object",
            "required": ["summary", "start", "end"],
            "properties": {
                "summary": {"type": "string", "description": "Event title"},
                "start": {"type": "object", "description": "Start time {dateTime: ISO8601, timeZone: string}"},
                "end": {"type": "object", "description": "End time {dateTime: ISO8601, timeZone: string}"},
                "location": {"type": "string"},
                "description": {"type": "string"},
                "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of email addresses"},
                "reminders": {"type": "object", "description": "Reminders: {useDefault: bool} or {overrides: [{method: 'popup'|'email', minutes: int}]}"},
            },
        },
    },
    "update_event": {
        "fn": update_event,
        "description": "Update an existing calendar event",
        "inputSchema": {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string"},
                "calendar_id": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "object"},
                "end": {"type": "object"},
                "location": {"type": "string"},
                "description": {"type": "string"},
            },
        },
    },
    "delete_event": {
        "fn": delete_event,
        "description": "Delete a calendar event",
        "inputSchema": {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string"},
                "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
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
                "serverInfo": {"name": "google-calendar", "version": "1.0.0"},
            }
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        tools = []
        for name, t in TOOLS.items():
            tools.append({
                "name": name,
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
        try:
            result = TOOLS[tool_name]["fn"](args)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": str(e), "data": traceback.format_exc()}
            }

    return {
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"}
    }


def main():
    # Trigger OAuth on first run (before entering stdio loop)
    # This opens browser if no token exists
    try:
        get_credentials()
    except Exception as e:
        sys.stderr.write(f"Auth error: {e}\n")
        sys.exit(1)

    for line in sys.stdin.buffer:
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
