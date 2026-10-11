import json

from src.chat_rooms import RealtimeClient, RoomRequest, SubscriberMessage, deliver_subscriber_update


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()


def test_publish_keeps_message_id_and_reads_envelope():
    seen = []

    def opener(request):
        seen.append((request.get_method(), request.full_url, json.loads(request.data)))
        return FakeResponse({"ok": True, "data": {"accepted": True}, "error": None, "metadata": {}})

    client = RealtimeClient(api_key="test-key", opener=opener)
    result = deliver_subscriber_update(client, SubscriberMessage("creator:maya", "acct-7", "post-1001", "New lesson is live"))
    assert result["data"]["accepted"] is True
    assert seen[0][0] == "POST"
    assert seen[0][2]["data"]["message_id"] == "post-1001"


def test_create_channel_omits_default_type_but_keeps_explicit_type():
    seen = []

    def opener(request):
        seen.append(json.loads(request.data))
        return FakeResponse({"ok": True, "data": {}, "error": None})

    client = RealtimeClient(api_key="test-key", opener=opener)
    client.create_channel(RoomRequest("creator:maya"))
    client.create_channel(RoomRequest("creator:maya", channel_type="private"))
    assert seen[0] == {"channel": "creator:maya", "vendor": "ably"}
    assert seen[1]["type"] == "private"
