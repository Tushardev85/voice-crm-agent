import asyncio
import json

import tools


class FakeResponse:
    def __init__(self, ok=True, text='{"ok": true}'):
        self.ok = ok
        self.text = text


def run(coro):
    return asyncio.run(coro)


def test_handle_tool_call_requires_workspace_context() -> None:
    result = json.loads(
        run(
            tools.handle_tool_call(
                "set_call_disposition",
                {"disposition": "no_answer"},
                {"lead_id": "lead-1"},
            )
        )
    )

    assert result == {
        "status": "error",
        "message": "No workspace context available",
    }


def test_connected_qualified_requires_bant_fields(monkeypatch) -> None:
    called = False

    def fake_post(*args, **kwargs):
        nonlocal called
        called = True
        return FakeResponse()

    monkeypatch.setattr(tools.requests, "post", fake_post)

    result = json.loads(
        run(
            tools.handle_tool_call(
                "set_call_disposition",
                {"disposition": "connected_qualified", "has_budget": True},
                {"workspace_id": "workspace-1", "lead_id": "lead-1"},
            )
        )
    )

    assert result["status"] == "error"
    assert "Budget, Authority, Need, and Timing" in result["message"]
    assert called is False


def test_connected_qualified_posts_activity_with_bant(monkeypatch) -> None:
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return FakeResponse()

    monkeypatch.setattr(tools, "BACKEND_URL", "http://backend.test")
    monkeypatch.setattr(tools.requests, "post", fake_post)

    result = json.loads(
        run(
            tools.handle_tool_call(
                "set_call_disposition",
                {
                    "disposition": "connected_qualified",
                    "notes": "Qualified during AI call.",
                    "has_budget": True,
                    "has_authority": True,
                    "has_need": True,
                    "has_timing": True,
                    "estimated_value": 25000,
                },
                {
                    "workspace_id": "workspace-1",
                    "lead_id": "lead-1",
                    "auth_header": "Bearer token",
                },
            )
        )
    )

    assert result == {
        "status": "success",
        "disposition": "connected_qualified",
    }
    assert captured["url"] == "http://backend.test/api/v1/activities/"
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "workspace-id": "workspace-1",
        "Authorization": "Bearer token",
    }
    assert captured["json"] == {
        "lead_id": "lead-1",
        "channel": "call",
        "type": "manual",
        "disposition": "connected_qualified",
        "notes": "Qualified during AI call.",
        "has_budget": True,
        "has_authority": True,
        "has_need": True,
        "has_timing": True,
        "estimated_value": 25000,
        "currency": "USD",
    }
    assert captured["timeout"] == 10


def test_schedule_callback_sets_callback_disposition(monkeypatch) -> None:
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json})
        return FakeResponse()

    monkeypatch.setattr(tools, "BACKEND_URL", "http://backend.test")
    monkeypatch.setattr(tools.requests, "post", fake_post)

    result = json.loads(
        run(
            tools.handle_tool_call(
                "schedule_callback",
                {
                    "callback_date": "2026-07-02",
                    "callback_time": "14:30",
                    "notes": "Lead asked for tomorrow afternoon.",
                },
                {"workspace_id": "workspace-1", "lead_id": "lead-1"},
            )
        )
    )

    assert result == {
        "status": "success",
        "disposition": "connected_call_back",
        "callback_scheduled": "2026-07-02T14:30:00",
    }
    assert captured["url"] == "http://backend.test/api/v1/activities/"
    assert captured["json"] == {
        "lead_id": "lead-1",
        "channel": "call",
        "type": "manual",
        "disposition": "connected_call_back",
        "notes": "Lead asked for tomorrow afternoon.",
        "callback_datetime": "2026-07-02T14:30:00",
    }


def test_log_conversation_summary_posts_activity_note(monkeypatch) -> None:
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json})
        return FakeResponse()

    monkeypatch.setattr(tools, "BACKEND_URL", "http://backend.test")
    monkeypatch.setattr(tools.requests, "post", fake_post)

    result = json.loads(
        run(
            tools.handle_tool_call(
                "log_conversation_summary",
                {"summary": "Lead asked for pricing and timeline."},
                {"workspace_id": "workspace-1", "lead_id": "lead-1"},
            )
        )
    )

    assert result == {"status": "success", "message": "Summary logged"}
    assert captured["url"] == "http://backend.test/api/v1/activities/"
    assert captured["json"] == {
        "lead_id": "lead-1",
        "channel": "call",
        "type": "manual",
        "notes": "Lead asked for pricing and timeline.",
    }
