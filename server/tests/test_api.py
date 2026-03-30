import json

from app.db.session import SessionLocal
from app.services.summary_worker import process_one_summary_task


AUTH = {"Authorization": "Bearer test-token"}


def create_workspace(client):
    response = client.post("/v1/workspaces", json={"name": "default"}, headers=AUTH)
    assert response.status_code == 201
    return response.json()


def read_sse(response_text: str) -> list[tuple[str, dict]]:
    items = []
    current_event = None
    for line in response_text.splitlines():
        if line.startswith("event: "):
            current_event = line.removeprefix("event: ")
        elif line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
            if current_event:
                items.append((current_event, payload))
                current_event = None
    return items


def test_requires_auth(client):
    response = client.get("/v1/workspaces")
    assert response.status_code == 401


def test_create_workspace_and_list(client):
    workspace = create_workspace(client)
    response = client.get("/v1/workspaces", headers=AUTH)
    assert response.status_code == 200
    assert response.json()[0]["id"] == workspace["id"]


def test_stream_message_creates_node_and_main_branch(client):
    workspace = create_workspace(client)
    response = client.post(
        f"/v1/workspaces/{workspace['id']}/messages/stream",
        json={"prompt": "hello"},
        headers=AUTH,
    )
    assert response.status_code == 200
    events = read_sse(response.text)
    assert any(event == "assistant_final" for event, _ in events)
    node_saved = next(data for event, data in events if event == "node_saved")
    tree = client.get(f"/v1/workspaces/{workspace['id']}/tree", headers=AUTH).json()
    assert tree["branches"][0]["name"] == "main"
    assert tree["nodes"][0]["id"] == node_saved["node_id"]


def test_branching_from_history_creates_auto_branch(client):
    workspace = create_workspace(client)
    first = client.post(
        f"/v1/workspaces/{workspace['id']}/messages/stream",
        json={"prompt": "first"},
        headers=AUTH,
    )
    first_node_id = next(data for event, data in read_sse(first.text) if event == "node_saved")["node_id"]

    second = client.post(
        f"/v1/workspaces/{workspace['id']}/messages/stream",
        json={"prompt": "second", "parent_node_id": first_node_id},
        headers=AUTH,
    )
    assert second.status_code == 200

    third = client.post(
        f"/v1/workspaces/{workspace['id']}/messages/stream",
        json={"prompt": "rewrite", "parent_node_id": first_node_id},
        headers=AUTH,
    )
    third_saved = next(data for event, data in read_sse(third.text) if event == "node_saved")

    tree = client.get(f"/v1/workspaces/{workspace['id']}/tree", headers=AUTH).json()
    assert len(tree["branches"]) == 2
    assert any(branch["head_node_id"] == third_saved["node_id"] for branch in tree["branches"])


def test_trace_and_summary_worker(client):
    workspace = create_workspace(client)
    response = client.post(
        f"/v1/workspaces/{workspace['id']}/messages/stream",
        json={"prompt": "tool:echo:demo"},
        headers=AUTH,
    )
    node_id = next(data for event, data in read_sse(response.text) if event == "node_saved")["node_id"]
    with SessionLocal() as db:
        assert process_one_summary_task(db) is True
    trace = client.get(f"/v1/workspaces/{workspace['id']}/nodes/{node_id}/trace", headers=AUTH)
    assert trace.status_code == 200
    body = trace.json()
    assert body["summary"].startswith("Assistant generated")
    assert any(event["event_type"] == "tool_call" for event in body["events"])
