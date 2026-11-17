# Contributing

Use Python 3.11+ and Node.js 18+. Follow README setup, install `requirements-dev.txt`, and run:

```bash
python -m pytest -q
npm run check
npm test
```

Keep changes focused. Add meaningful tests when changing validation, storage, imports, or library behavior. Use a separate `TRAILMARK_DATABASE` path for experiments; never commit personal data or backup files.

The frontend intentionally uses browser-native modules without a framework or build step. Pure library logic lives in `trailmark/static/library.js`; DOM and network behavior lives in `app.js`.

For a roadmap feature, discuss its acceptance criteria in an issue first. Update README's status table only when the feature works end to end. Before submitting a pull request, describe the behavior change, verification performed, and remaining limitations.
