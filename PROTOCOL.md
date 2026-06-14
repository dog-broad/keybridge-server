# KeyBridge wire protocol

This document defines the protocol the server speaks with a paired client over the
WebSocket connection. It is the contract: a client and this server must agree on the
envelope shape exactly.

Transport is a single WebSocket connection carrying UTF-8 JSON text frames.

## Two planes

The connection carries two kinds of messages:

- **Input / delivery** — the versioned envelope described below. Every keystroke,
  combination, and block of text travels in an envelope, and the server confirms each
  one with an acknowledgement (`ack`). This is the reliability contract.
- **Session control** — connection setup and keep-alive: the handshake the server
  sends on connect, the client's authentication message, and keep-alive ping/pong.
  These are flat JSON objects (keyed by `command` / `type`) and are **not** wrapped in
  the envelope. They are described under [Session control](#session-control).

A receiver tells the two apart by shape: a message that carries `v`, `type`, and
`payload` is an envelope and is routed as input/ack; anything else is session control.

## The envelope

```jsonc
{
  "v": 1,            // protocol version (integer)
  "id": "uuid",      // unique per logical message; idempotency key
  "seq": 0,          // 0-based chunk index within the message
  "total": 1,        // total number of chunks in the message
  "type": "type",    // type | key_press | key_release | key_combo | ack
  "payload": { }     // type-specific body (absent on ack)
}
```

| Field | Meaning |
|---|---|
| `v` | Envelope version. This server speaks `v: 1`. A message with any other `v` is rejected with an error ack and is not applied. |
| `id` | Identifies one logical message (a key, a combo, or one block of text). All chunks of the same message share the same `id`. |
| `seq` | Chunk index, `0`-based. A single-chunk message uses `seq: 0`. |
| `total` | How many chunks make up the message. A single-chunk message uses `total: 1`. |
| `type` | The input family (or `ack`). |
| `payload` | The body for that `type`. |

`v`, `id`, `seq`, `total`, and `type` are required on every input envelope.

## Input types

### `type` — type text

```json
{ "v": 1, "id": "…", "seq": 0, "total": 1, "type": "type",
  "payload": { "text": "Hello, World!", "delay_ms": 0 } }
```

`payload.text` is the text to type (full Unicode). `payload.delay_ms` is an optional
per-character delay in milliseconds; `0` or absent means type at full speed.

### `key_press` / `key_release` — one key down / up

```json
{ "v": 1, "id": "…", "seq": 0, "total": 1, "type": "key_press",
  "payload": { "key": "shift" } }
```

`payload.key` is a key name (see [Supported keys](README.md#supported-keys)) or a
single character.

### `key_combo` — a chord

```json
{ "v": 1, "id": "…", "seq": 0, "total": 1, "type": "key_combo",
  "payload": { "keys": ["ctrl", "c"] } }
```

The server presses the keys in order, then releases them in reverse order.

## Acknowledgement

The server sends one ack per chunk it has applied, back to the client:

```jsonc
{ "v": 1, "type": "ack", "id": "…", "seq": 0, "status": "ok" }
{ "v": 1, "type": "ack", "id": "…", "seq": 0, "status": "error", "error": "…" }
```

- `status: "ok"` — the chunk was applied.
- `status: "error"` — the chunk could not be applied; `error` is a human-readable
  reason. The client keeps the input and may retry or surface the failure.

An ack carries no `payload`. It echoes the `id` and `seq` of the chunk it confirms so
the client can match it to the chunk it sent.

## Long text: chunking and progress

A long block of text is split by the client into ordered chunks that share one `id`,
with `seq` running `0 … total-1`. The server applies the chunks **in order** and acks
each one as it is applied, so the client can show progress that advances toward
`total`. The reference client splits on Unicode code-point boundaries at up to a few
hundred code points per chunk; the server applies whatever `seq`/`total` a client
sends and does not assume a fixed chunk size.

## Idempotency and retry

Delivery is confirmed, and retries are safe:

- The server remembers the `(id, seq)` pairs it has already applied, per connection, in
  a bounded set (the most recent entries; older ones are evicted, and the set is
  cleared when the connection closes).
- If a chunk arrives whose `(id, seq)` was already applied, the server **re-acks it but
  does not apply it again**. So a client that resends a chunk whose ack was lost gets a
  fresh confirmation without the text being typed twice.

Because of this, a client may retry an un-acked chunk by resending the **same**
envelope (same `id` and `seq`). Retries are expected to be bounded by the client.

## Errors

A malformed or unsupported envelope produces an error ack (for input with an `id`) or a
flat error object (when no envelope `id` is available):

```json
{ "status": "error", "message": "…" }
```

Examples: unknown `v`, missing required envelope fields, an unsupported `type`, or an
unsupported key.

## Session control

These messages are flat (not enveloped) and handle connection lifecycle.

On connect, the server sends a handshake:

```json
{ "type": "handshake", "protocol_version": "2.0",
  "features": { "authentication": true, "encryption": true, "compression": true },
  "session_id": "…" }
```

If authentication is enabled, the client authenticates with the token carried in the
pairing QR code:

```json
{ "command": "authenticate", "token": "…" }
```

Keep-alive uses a ping the client sends periodically; the server replies with a pong
and extends the connection's idle timeout:

```json
{ "command": "ping", "timestamp": 1701234567890 }
```

## Encryption

When message encryption is enabled, the serialized envelope (or control message) is the
plaintext that is encrypted before being put on the wire, and decrypted on receipt. The
envelope shape above describes the decrypted message. Encryption is a transport concern
layered around the protocol; it does not change the envelope.
