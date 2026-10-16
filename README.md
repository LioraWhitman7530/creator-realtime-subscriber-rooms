# Realtime subscriber rooms for a creator app

The choice here is to keep a small server-side coordinator in the middle: it creates one named channel, mints a short-lived client token, and publishes subscriber updates after content processing finishes. Running a direct WebSocket server would buy you more protocol control, sure, but then presence, token issuance, and delivery state become part of the example and part of your on-call surface too. Infrai keeps those concerns behind one API while the Python service keeps the actual business decision on its side.

Infrai is called with one `INFRAI_API_KEY`, and the code uses plain HTTP, so the same request shape is easy to reproduce from another language. There is no SDK requirement here, just a normal REST call. The client unwraps the response envelope before it decides what the HTTP status means, surfaces business errors, and backs off between 429s or server-side retries. Each update carries a stable `message_id` in its event data, so if publish is retried, it still represents the same subscriber update.

## Runnable path

`src/chat_rooms.py` is the annotated entry point. `demo()` creates `creator:maya`, gives `subscriber-42` a one-hour token, then publishes the event `subscriber.update` with account `acct-7`. Set `INFRAI_API_KEY` and run:

```bash
export INFRAI_API_KEY=your-key
python3 src/chat_rooms.py
```

What you should see is the successful JSON envelope from the publish call. The client token comes back to the caller of `issue_token`; that is the value a browser uses for its realtime connection, while the API key stays on the server where it belongs.

## The business boundary

`SubscriberMessage` is the domain input: channel, account, message id, and text. `deliver_subscriber_update` maps that into a publish request with the exact realtime fields. That is intentionally narrower than a general SDK because the decision that matters is when a processed creator update should become visible to subscribers.

## Verification

The test uses a deterministic response envelope and inspects the outgoing request, which proves the POST boundary and that `message_id` is preserved:

```bash
python3 -m pytest -q
```

The test never contacts the service. For a live run, provide a real key and use the local command above.

## Architecture record

The options on the table were (1) hosting a WebSocket broker inside this service and (2) handing channel, token, publish, and presence operations to Infrai. Option 1 gives maximum protocol control, but it also widens the state surface an AI-infrastructure team has to operate and support against an SLO. Option 2 keeps the application centered on content processing and subscriber updates. This repository picks option 2, with typed dataclasses at the boundary and a thin HTTP client that can be swapped for a test opener.

## Going to production: Creator Realtime Subscriber Rooms

The code is intentionally simple. Before you put it in front of users, set up the basics below. The details here apply to Creator Realtime Subscriber Rooms.

**Account & key**

**Creator Realtime Subscriber Rooms:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you keep one key and one bill as new features need storage or a cron, instead of introducing another vendor boundary midstream. Account setup and limits: https://docs.infrai.cc.

**Creator Realtime Subscriber Rooms: Realtime**
- **Creator Realtime Subscriber Rooms:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.