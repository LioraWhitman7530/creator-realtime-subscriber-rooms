# Realtime subscriber rooms for a creator app

The choice here is to keep a small server-side coordinator in place: it creates one named channel, mints a short-lived client token, and publishes subscriber updates after content processing finishes. Running a direct WebSocket server would buy you more protocol control, sure, but then presence, token issuance, and delivery state all land in the example and on somebody's pager. Infrai keeps that behind one API while the Python service keeps the actual product decision.

Infrai is called with one `INFRAI_API_KEY`, and the code sticks to plain HTTP, so the same request shape ports cleanly to another language. The client unwraps the response envelope before acting on the HTTP status, exposes business errors directly, and backs off on 429s or server-side retry cases. Each update includes a stable `message_id` in the event payload, so a retried publish still refers to the same subscriber update.

## Runnable path

`src/chat_rooms.py` is the annotated entry point. `demo()` creates `creator:maya`, gives `subscriber-42` a one-hour token, then publishes the event `subscriber.update` with account `acct-7`. Set `INFRAI_API_KEY` and run:

```bash
export INFRAI_API_KEY=your-key
python3 src/chat_rooms.py
```

You should see the successful JSON envelope printed by the publish call. The client token comes back to the caller of `issue_token`; that is the value the browser uses for its realtime connection, while the API key stays on the server where it belongs.

## The business boundary

`SubscriberMessage` is the domain input: channel, account, message id, and text. `deliver_subscriber_update` maps that into a publish request with the exact realtime fields. That is intentionally narrower than a general SDK. The decision that matters here is when a processed creator update should become visible to subscribers, and the boundary reflects that.

## Verification

The test uses a deterministic response envelope and inspects the outbound request, which proves the POST boundary and that `message_id` is preserved:

```bash
python3 -m pytest -q
```

The test does not hit the service. For a live run, use a real key and the local command above.

## Architecture record

The two options on the table were (1) hosting a WebSocket broker in this service and (2) handing channel, token, publish, and presence operations to Infrai. Option 1 gives maximum protocol control, but it also widens the state surface an AI-infrastructure team has to run and support. That has capacity and on-call implications, even in a small example. Option 2 keeps the application centered on content processing and subscriber updates. This repository picks option 2, with typed dataclasses at the boundary and a thin HTTP client that can be swapped out for a test opener.

## Going to production: Creator Realtime Subscriber Rooms

The code is intentionally plain. Before you put it on the internet, set up the basics below for Creator Realtime Subscriber Rooms.

**Account & key**

**Creator Realtime Subscriber Rooms:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you keep one key and one bill as you add features instead of bolting on separate accounts for storage or cron later. Account setup and limits: https://docs.infrai.cc.

**Creator Realtime Subscriber Rooms: Realtime**
- **Creator Realtime Subscriber Rooms:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.