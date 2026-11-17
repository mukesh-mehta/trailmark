# Trailmark API

Base URL: `http://127.0.0.1:5000`. All responses are JSON except successful DELETE (empty body). This is a local, single-user API, not an authenticated public service.

Mutation requests require `X-Trailmark-Request: 1`. POST/PATCH also require `Content-Type: application/json`. Browser origins must match the server origin; cross-origin access is not enabled. The custom header is a browser request safeguard, not an authentication token.

| Method | Path | Result |
|---|---|---|
| GET | `/api/health` | `{ "status": "ok", "version": "0.1.0" }` |
| GET | `/api/resources` | `{ "resources": [...] }`, newest first |
| POST | `/api/resources` | Create a resource; returns it with status 201 |
| PATCH | `/api/resources/<id>` | Update supplied fields; returns the full resource |
| DELETE | `/api/resources/<id>` | Remove the resource; status 204 |
| GET | `/api/export` | Download all records as a versioned JSON backup |
| POST | `/api/import` | Validate then merge a backup; returns imported/skipped counts |

Filtering and sorting are browser-side in this release; list endpoints do not accept filter or pagination parameters.

## Resource fields

| Field | Rules |
|---|---|
| `title` | Required nonblank text, at most 160 characters |
| `url` | Required HTTP(S) URL, at most 2,048 characters; no embedded credentials; unique after normalization |
| `kind` | `article` (default), `video`, `course`, `tool`, or `book` |
| `status` | `queued` (default), `learning`, or `completed` |
| `tags` | Array of at most 12 nonblank strings, each at most 30 characters; trimmed, lowercased, deduplicated |
| `notes` | Plain text, at most 10,000 characters; default empty |
| `favorite` | Boolean; default `false` |
| `id` | Server-generated integer, read-only |
| `created_at`, `updated_at` | Server-generated UTC ISO timestamps, read-only |

Unknown input fields are rejected. PATCH preserves omitted fields. Import accepts the read-only fields from exports but regenerates them.

## Example

```bash
curl -X POST http://127.0.0.1:5000/api/resources \
  -H 'Content-Type: application/json' \
  -H 'X-Trailmark-Request: 1' \
  -d '{"title":"Python tutorial","url":"https://docs.python.org/3/tutorial/","kind":"course","tags":["python"],"status":"learning"}'
```

```json
{
  "schema_version": 1,
  "resources": [
    {
      "title": "Python tutorial",
      "url": "https://docs.python.org/3/tutorial/",
      "kind": "course",
      "status": "learning",
      "tags": ["python"],
      "notes": "Work through the examples.",
      "favorite": true
    }
  ]
}
```

Save that JSON as a backup file and use the Import button, or POST it to `/api/import`. Success returns `{"imported":1,"skipped":0}`. Duplicate URLs within the file or already in the database are skipped. All validation runs before any write.

## Errors

Client errors use `{"error":"Readable explanation."}`:

- `400`: malformed JSON, invalid field, unsupported backup format, or untrusted host.
- `403`: missing request header or cross-origin mutation.
- `404`: resource or endpoint not found.
- `409`: duplicate URL on create/update.
- `413`: body exceeds 1 MiB.
- `415`: POST/PATCH body is not JSON.

Operational failures such as a read-only disk may produce a server error. The interface retains unsaved form content and offers a retry for load failures.
