"""
CRM tool definitions for OpenAI function-calling in the agent pipeline.

These tools allow the AI agent to interact with the voice-crm backend during
a conversation, enabling it to set dispositions, log activities, and update
lead information after the call.
"""

import os
import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "https://app.finhubb.io")


def _backend_headers(workspace_id: str) -> dict:
    """Headers for backend API calls from the agent (service-level)."""
    return {
        "Content-Type": "application/json",
        "workspace-id": workspace_id,
    }


CRM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_call_disposition",
            "description": (
                "Set the outcome/disposition of the current call with the lead. "
                "Use this when the conversation reaches a clear outcome."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "disposition": {
                        "type": "string",
                        "enum": [
                            "no_answer",
                            "left_voicemail",
                            "busy",
                            "connected_call_back",
                            "connected_qualified",
                            "connected_not_interested",
                            "connected_disqualified",
                        ],
                        "description": "The call outcome disposition.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Brief summary of the conversation.",
                    },
                },
                "required": ["disposition"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_callback",
            "description": (
                "Schedule a follow-up callback with the lead. "
                "Use when the lead wants to be called back at a specific date/time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "callback_date": {
                        "type": "string",
                        "description": "The date for the callback in YYYY-MM-DD format.",
                    },
                    "callback_time": {
                        "type": "string",
                        "description": "The time for the callback in HH:MM format (24h).",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes about the callback request.",
                    },
                },
                "required": ["callback_date", "callback_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_conversation_summary",
            "description": (
                "Log a summary of the conversation as an activity note on the lead. "
                "Use at the end of every conversation to ensure audit trail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A concise summary of the conversation.",
                    },
                    "lead_interested": {
                        "type": "boolean",
                        "description": "Whether the lead expressed interest.",
                    },
                },
                "required": ["summary"],
            },
        },
    },
]


async def handle_tool_call(
    function_name: str,
    arguments: dict,
    call_metadata: dict,
) -> str:
    """
    Execute a CRM tool call and return the result as a string for the LLM.

    call_metadata should contain: lead_id, workspace_id, agent_id
    """
    lead_id = call_metadata.get("lead_id")
    workspace_id = call_metadata.get("workspace_id")

    if not workspace_id:
        return json.dumps({"status": "error", "message": "No workspace context available"})

    try:
        if function_name == "set_call_disposition":
            return await _set_disposition(workspace_id, lead_id, arguments)
        elif function_name == "schedule_callback":
            return await _schedule_callback(workspace_id, lead_id, arguments)
        elif function_name == "log_conversation_summary":
            return await _log_summary(workspace_id, lead_id, arguments)
        else:
            return json.dumps({"status": "error", "message": f"Unknown function: {function_name}"})
    except Exception as e:
        logger.error(f"Tool call failed: {function_name}: {e}")
        return json.dumps({"status": "error", "message": str(e)})


async def _set_disposition(workspace_id: str, lead_id: Optional[str], args: dict) -> str:
    if not lead_id:
        return json.dumps({"status": "skipped", "message": "No lead_id associated with this call"})

    payload = {
        "disposition": args["disposition"],
        "notes": args.get("notes"),
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/leads/{lead_id}/dispose",
            headers=_backend_headers(workspace_id),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            return json.dumps({"status": "success", "disposition": args["disposition"]})
        return json.dumps({"status": "error", "message": resp.text[:200]})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def _schedule_callback(workspace_id: str, lead_id: Optional[str], args: dict) -> str:
    if not lead_id:
        return json.dumps({"status": "skipped", "message": "No lead_id associated with this call"})

    callback_datetime = f"{args['callback_date']}T{args['callback_time']}:00"
    payload = {
        "disposition": "connected_call_back",
        "notes": args.get("notes", "Callback requested during AI conversation"),
        "callback_datetime": callback_datetime,
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/leads/{lead_id}/dispose",
            headers=_backend_headers(workspace_id),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            return json.dumps({"status": "success", "callback_scheduled": callback_datetime})
        return json.dumps({"status": "error", "message": resp.text[:200]})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


async def _log_summary(workspace_id: str, lead_id: Optional[str], args: dict) -> str:
    if not lead_id:
        return json.dumps({"status": "skipped", "message": "No lead_id — summary logged locally only"})

    payload = {
        "lead_id": lead_id,
        "channel": "call",
        "type": "manual",
        "notes": args["summary"],
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/activities/",
            headers=_backend_headers(workspace_id),
            json=payload,
            timeout=10,
        )
        if resp.ok:
            return json.dumps({"status": "success", "message": "Summary logged"})
        return json.dumps({"status": "error", "message": resp.text[:200]})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
