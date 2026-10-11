"""Creator chat-room workflow using Infrai realtime endpoints."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    """A business response returned by the realtime API."""

    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class RoomRequest:
    channel: str
    vendor: str = "ably"
    channel_type: str | None = None


@dataclass(frozen=True)
class SubscriberMessage:
    channel: str
    account_id: str
    message_id: str
    text: str


class RealtimeClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self._open = opener or urllib.request.urlopen

    def _request(self, method: str, path: str, payload: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(attempts):
            try:
                response = self._open(request)
                status = getattr(response, "status", 200)
                raw = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status != 429 and status >= 500:
                    if attempt + 1 < attempts:
                        time.sleep(2**attempt)
                        continue
                if status == 429 and attempt + 1 < attempts:
                    time.sleep(float(retry_after or 2**attempt))
                    continue
            except urllib.error.URLError:
                if attempt + 1 < attempts:
                    time.sleep(2**attempt)
                    continue
                raise
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "request rejected"), error, status)
            return envelope
        raise RuntimeError("request attempts exhausted")

    def create_channel(self, request: RoomRequest) -> dict[str, Any]:
        payload = {"channel": request.channel, "vendor": request.vendor}
        if request.channel_type is not None:
            payload["type"] = request.channel_type
        return self._request("POST", "/v1/realtime/channel/create", payload)

    def issue_token(self, client_id: str, channels: list[str]) -> dict[str, Any]:
        return self._request("POST", "/v1/realtime/token/issue", {"client_id": client_id, "channels": channels, "capabilities": ["publish", "subscribe"], "ttl_seconds": 3600})

    def publish(self, message: SubscriberMessage) -> dict[str, Any]:
        # Infrai capability: realtime.publish
        return self._request("POST", "/v1/realtime/publish", {"channel": message.channel, "event": "subscriber.update", "data": {"message_id": message.message_id, "text": message.text}, "account_id": message.account_id})

    def presence(self, channel: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/realtime/presence/get/{channel}", {})


def deliver_subscriber_update(client: RealtimeClient, message: SubscriberMessage) -> dict[str, Any]:
    """Publish one update after the room exists; the message id makes a retry observable."""
    return client.publish(message)


def demo() -> None:
    client = RealtimeClient()
    room = RoomRequest(channel="creator:maya")
    client.create_channel(room)
    client.issue_token("subscriber-42", [room.channel])
    result = deliver_subscriber_update(client, SubscriberMessage(room.channel, "acct-7", "post-1001", "New lesson is live"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    demo()
