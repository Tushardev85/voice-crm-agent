from fastapi.testclient import TestClient


def test_get_index(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"message": "Successfully running Cat."}


def test_post_index(client: TestClient) -> None:
    res = client.post("/")
    assert res.status_code == 405


def test_agent_twiml_includes_websocket_stream_and_call_id(
    client: TestClient,
) -> None:
    res = client.post(
        "/agent?call_id=call-123", headers={"host": "voice.example.test"}
    )

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    assert '<Stream url="wss://voice.example.test/ws">' in res.text
    assert '<Parameter name="call_id" value="call-123" />' in res.text


def test_agent_twiml_omits_empty_call_id(client: TestClient) -> None:
    res = client.post("/agent", headers={"host": "voice.example.test"})

    assert res.status_code == 200
    assert '<Stream url="wss://voice.example.test/ws">' in res.text
    assert '<Parameter name="call_id"' not in res.text


def test_proxy_call_status_webhook_forwards_body(
    monkeypatch, client: TestClient
) -> None:
    import app as app_module

    captured = {}

    class FakeResponse:
        text = '{"ok": true}'
        status_code = 202
        headers = {"content-type": "application/json"}

    def fake_post(url, data, headers, timeout):
        captured.update(
            {
                "url": url,
                "data": data,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setenv("BACKEND_URL", "http://backend.test/")
    monkeypatch.setattr(app_module.requests, "post", fake_post)

    res = client.post(
        "/api/v1/call/webhook",
        content=b"CallSid=CA123&CallStatus=in-progress",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )

    assert res.status_code == 202
    assert res.json() == {"ok": True}
    assert captured["url"] == "http://backend.test/api/v1/call/webhook"
    assert captured["data"] == b"CallSid=CA123&CallStatus=in-progress"
    assert captured["headers"] == {
        "content-type": "application/x-www-form-urlencoded"
    }
    assert captured["timeout"] == 10
