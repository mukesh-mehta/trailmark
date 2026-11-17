# Roadmap

The local library is usable today. These three optional extensions are **not implemented**. They are documented here rather than exposed as non-working controls. See README for the nine completed features.

## 10. Automatic link metadata

Fetch a suggested page title and description when the user explicitly requests it. Keep every field editable and retain manual entry.

Acceptance criteria:

- Network failures, unsupported pages, and timeouts never prevent manual saving.
- Requests cannot reach private, loopback, link-local, or cloud metadata addresses; redirects and resolved addresses must also be checked.
- Bound response size, redirects, and duration. Fetch only HTML over HTTP(S).
- Render returned metadata as plain text and test invalid or hostile responses.

## 11. Browser extension

Provide an extension popup that sends the current tab's title and URL to the local app after a user click.

Acceptance criteria:

- Limit permissions to the active tab and an explicitly configured Trailmark origin.
- Define a deliberate local authentication and origin policy instead of broadly enabling CORS.
- Explain when the local app is offline and allow retries without duplicate entries.
- Keep the normal Add resource form independent of the extension.

## 12. Accounts and cross-device sync

Introduce authenticated libraries as an optional deployment mode, with local single-user mode still supported.

Acceptance criteria:

- Add schema migrations and isolate every read/write by owner.
- Define authentication, session expiration, CSRF protection, and account recovery.
- Specify conflict resolution and backup behavior before syncing across devices.
- Add integration tests for unauthorized access and cross-user data leakage.
- Document a production server and secret management; do not treat this local server as a hosted service.
