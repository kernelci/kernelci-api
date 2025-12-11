# Event System Migration Guide

This document describes the migration from Redis-only pub/sub to MongoDB-backed
durable event delivery using the unified `eventhistory` collection.

## Overview

The KernelCI API event system has been upgraded to support **durable event
delivery**. This is an opt-in feature that allows subscribers to receive missed
events after reconnection, solving the problem of lost events during:

- Subscriber restarts or crashes
- Redis restarts
- Network interruptions
- Delayed subscriber startup (e.g., scheduler starting after kbuild publishes)

## Architecture Change

Previously, events were stored in two places:
1. Redis pub/sub (real-time, fire-and-forget)
2. `eventhistory` collection (for `/events` API, 24h TTL)

Now, there is a **unified event storage**:
- `eventhistory` collection serves both `/events` API AND durable pub/sub
- Redis pub/sub used only for real-time notification
- Extended TTL (7 days default, configurable)

## Two Modes of Operation

### 1. Fire-and-Forget Mode (Default, Backwards Compatible)

This is the original behavior. Events are delivered via Redis pub/sub and lost
if no subscriber is listening.

```bash
# Subscribe without subscriber_id - original behavior
curl -X POST "https://api.kernelci.org/subscribe/node" \
  -H "Authorization: Bearer $TOKEN"
```

**Characteristics:**
- Real-time delivery via Redis
- Events lost if subscriber not connected
- No position tracking
- Suitable for dashboards and non-critical consumers

### 2. Durable Mode (New, Opt-in)

Events are stored in MongoDB and delivered reliably. Subscribers track their
position and receive missed events on reconnection.

```bash
# Subscribe with subscriber_id - durable delivery
curl -X POST "https://api.kernelci.org/subscribe/node?subscriber_id=scheduler-prod-1" \
  -H "Authorization: Bearer $TOKEN"
```

**Characteristics:**
- Events stored in `eventhistory` collection (7-day TTL)
- Missed events delivered on reconnection (up to 1000 by default)
- Implicit acknowledgment when polling for next event
- Suitable for critical consumers like schedulers

## API Changes

### Subscribe Endpoint

New optional parameter `subscriber_id`:

```
POST /subscribe/{channel}?subscriber_id={unique_id}&promisc={bool}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| channel | string | Yes | Channel name (e.g., "node") |
| subscriber_id | string | No | Unique ID for durable delivery |
| promisc | bool | No | Receive all messages regardless of owner |

### /events Endpoint

The `/events` endpoint continues to work unchanged. New fields are added to
each event document but do not affect existing queries:

```json
{
  "id": "mongo_object_id",
  "timestamp": "2025-01-15T10:30:00Z",
  "sequence_id": 12345,           // NEW - for pub/sub ordering
  "channel": "node",              // NEW - channel name
  "owner": "kbuild",              // NEW - event publisher
  "data": {
    "op": "created",
    "id": "node_id",
    "kind": "checkout",
    "state": "running",
    ...
  }
}
```

Existing queries filtering on `timestamp`, `data.kind`, `data.state`, etc.
continue to work unchanged.

Supported query parameters for `/events`:

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | string (ISO timestamp) | Return events with `timestamp` greater than this value. |
| `kind` | string | Filter by `data.kind` (e.g., `job`, `node`). |
| `state` | string | Filter by `data.state`. |
| `result` | string | Filter by `data.result`. |
| `limit` | integer | Maximum number of events to return. |
| `recursive` | bool | Attach related node info to each event (max `limit` 1000). |
| `id` | string (Mongo ObjectId) | Filter by a single event document id. |
| `ids` | string (comma‑separated ObjectIds) | Filter by multiple event document ids. |

## Subscriber ID Guidelines

The `subscriber_id` should be:
- **Unique** per subscriber instance
- **Stable** across restarts (same ID = resume from last position)
- **Descriptive** for debugging

Examples:
```
scheduler-prod-1
scheduler-prod-2
dashboard-main
test-runner-arm64
```

Multiple instances of the same service should use different subscriber_ids:
```
scheduler-prod-1  # Instance 1
scheduler-prod-2  # Instance 2
```

## How Durable Delivery Works

### Event Flow

```
Publisher                  eventhistory            Redis              Subscriber
    |                         collection              |                    |
    |-- publish_cloudevent() -->|                     |                    |
    |                           |-- store event       |                    |
    |                           |   (sequence_id,     |                    |
    |                           |    channel, owner)  |                    |
    |                           |                     |<-- publish --------|
    |                           |                     |                    |
    |                           |                     |-- real-time msg -->|
```

### Subscriber Reconnection

```
Subscriber (after restart)         API                    MongoDB
         |                          |                        |
         |-- subscribe(id=X) ----->|                        |
         |                          |-- get subscriber state |
         |                          |<-- last_seq_id=100 ----|
         |                          |                        |
         |                          |-- get events > 100 --->|
         |                          |<-- [101, 102, 103] ----|
         |                          |                        |
         |<-- event 101 -----------|                        |
         |<-- event 102 -----------|                        |
         |<-- event 103 -----------|                        |
         |                          |                        |
         |   (then real-time)       |                        |
```

### Implicit Acknowledgment

When a subscriber polls for the next event, the previous event is implicitly
acknowledged:

```
Time    Action                          Effect
----    ------                          ------
T1      GET /listen/1                   Wait for event
T2      Receive event seq_id=100        last_delivered_id = 100
T3      Process event                   (application logic)
T4      GET /listen/1                   ACK event 100, wait for next
                                        last_event_id = 100 (saved)
```

If the subscriber crashes between T2 and T4, event #100 will be redelivered
on reconnection. **Subscribers must be idempotent.**

## Migration Steps

### Step 1: Apply kernelci-core Patch

Apply the EventHistory model patch to add new fields:

```bash
cd ~/Documents/COLLABORA/DUAL/kernelci-core
git apply /path/to/eventhistory.patch
```

This adds:
- `sequence_id`: Sequential ID for pub/sub ordering
- `channel`: Channel name (default: "node")
- `owner`: Event publisher username
- Extended TTL: 7 days (was 24 hours), configurable via `EVENT_HISTORY_TTL_SECONDS`

### Step 2: Update KernelCI API

The API changes are already in place:
- `pubsub_mongo.py`: New hybrid pub/sub implementation
- `main.py`: Updated to use unified event storage
- `models.py`: Added `SubscriberState` model

### Step 3: Automatic Migration (On First Startup)

The API automatically detects and migrates the old eventhistory format:

1. **Detection**: Checks for old 24h TTL index (`expireAfterSeconds: 86400`)
2. **Migration**: If detected:
   - Drops all old indexes
   - Deletes old documents (they lack required fields)
   - Creates new indexes with 7-day TTL

**What you'll see in logs:**
```
WARNING - Detected old eventhistory format (24h TTL). Migration required.
WARNING - Migrating eventhistory collection to new format...
INFO - Dropping index: timestamp_1
INFO - Deleted 12345 old eventhistory documents
INFO - eventhistory migration complete
```

**Note**: This loses at most 24 hours of event history (old TTL). The `/events`
endpoint will return empty until new events are published.

#### Manual Migration (Optional)

If you prefer to migrate manually before deploying:

```javascript
// Connect to MongoDB
use kernelci

// Drop old index (24h TTL)
db.eventhistory.dropIndex("timestamp_1")

// Delete old documents (lack sequence_id, channel, owner)
db.eventhistory.deleteMany({})

// Create new indexes (also created by API on startup):
db.eventhistory.createIndex(
  {"timestamp": 1},
  {expireAfterSeconds: 604800, name: "ttl_timestamp"}
)
db.eventhistory.createIndex(
  {"channel": 1, "sequence_id": 1},
  {name: "channel_sequence_id"}
)

// Create subscriber state indexes
db.subscriber_state.createIndex(
  {"subscriber_id": 1},
  {unique: true, name: "unique_subscriber_id"}
)
db.subscriber_state.createIndex(
  {"last_poll": 1},
  {name: "last_poll"}
)
```

### Step 4: Update Clients

For clients that need durable delivery, add `subscriber_id`:

```python
# Before (fire-and-forget)
response = requests.post(f"{API}/subscribe/node", headers=auth)

# After (durable)
response = requests.post(
    f"{API}/subscribe/node?subscriber_id=my-scheduler-1",
    headers=auth
)
```

Make handlers idempotent:

```python
def handle_build_complete(event):
    node_id = event['node_id']

    # Check if already processed
    if is_already_scheduled(node_id):
        return  # Skip duplicate

    schedule_tests(node_id)
```

## Configuration

### Environment Variables

```bash
# Event retention period (default: 7 days)
EVENT_HISTORY_TTL_SECONDS=604800

# Max events to deliver on reconnection (default: 1000)
# (hardcoded in pubsub_mongo.py, modify if needed)
```

## MongoDB Collections

### eventhistory (Extended)

Stores all published events for both `/events` API and durable pub/sub.

```javascript
{
    "_id": ObjectId("..."),
    "timestamp": ISODate("2025-01-15T10:30:00Z"),
    "sequence_id": 12345,           // NEW - sequential ID
    "channel": "node",              // NEW - channel name
    "owner": "kbuild",              // NEW - publisher username
    "data": {
        "op": "created",
        "id": "node_id",
        "kind": "checkout",
        ...
    }
}
```

Indexes:
- `timestamp`: TTL index (7 days default)
- `channel, sequence_id`: Compound index for catch-up queries

### subscriber_state (New)

Tracks subscriber positions for durable subscriptions.

```javascript
{
    "subscriber_id": "scheduler-prod-1",
    "channel": "node",
    "user": "admin",
    "promiscuous": false,
    "last_event_id": 12340,
    "created_at": ISODate("..."),
    "last_poll": ISODate("...")
}
```

Indexes:
- `subscriber_id`: Unique index
- `last_poll`: Cleanup index

## Storage Estimates

Based on ~155,000 nodes/day with ~5 events per node:

| Retention | Events | Storage |
|-----------|--------|---------|
| 1 day | 775,000 | ~390 MB |
| 7 days | 5,425,000 | ~2.7 GB |
| 30 days | 23,250,000 | ~11.6 GB |

Recommended: Use default 7-day TTL (~2.7 GB).

## Troubleshooting

### Subscriber not receiving missed events

1. Check subscriber_id is provided:
   ```bash
   curl -X POST ".../subscribe/node?subscriber_id=my-id" ...
   ```

2. Verify subscriber state exists:
   ```javascript
   db.subscriber_state.findOne({subscriber_id: "my-id"})
   ```

3. Check events exist in range:
   ```javascript
   db.eventhistory.find({
       channel: "node",
       sequence_id: {$gt: LAST_SEQ_ID}
   }).count()
   ```

### Events being redelivered repeatedly

Ensure your handler completes successfully. Events are only acknowledged
when you poll for the next one. If your handler crashes repeatedly, you'll
keep receiving the same event.

### /events endpoint returning extra fields

This is expected. The new fields (`sequence_id`, `channel`, `owner`) are
additions for pub/sub functionality. Existing clients should ignore unknown
fields.

### High MongoDB disk usage

1. Check eventhistory size:
   ```javascript
   db.eventhistory.stats().storageSize
   ```

2. Verify TTL index exists:
   ```javascript
   db.eventhistory.getIndexes()
   // Should include: {key: {timestamp: 1}, expireAfterSeconds: 604800}
   ```

3. Reduce TTL if needed:
   ```bash
   EVENT_HISTORY_TTL_SECONDS=259200  # 3 days
   ```

## Rollback

To revert to the old behavior:

1. Update `api/main.py`:
   ```python
   # Change:
   from .pubsub_mongo import PubSub
   # Back to:
   from .pubsub import PubSub
   ```

2. Restore the `_get_eventhistory` function and `db.create(evhist)` calls

3. Restart API servers

4. (Optional) Clean up subscriber state:
   ```javascript
   db.subscriber_state.drop()
   ```

Note: After rollback, all clients revert to fire-and-forget mode regardless
of subscriber_id parameter.
