# Verification record

Verified locally on 16 November 2026 with Python 3.12 and Node.js 18.

Before the initial GitHub push on 17 November 2026, all 35 Python tests, five JavaScript tests, and JavaScript syntax checks passed again. Browser observations below are from 16 November.

- Python API integration suite: passing; covers persistence, CRUD, validation, imports, backups, request boundaries, and optional seed data.
- JavaScript syntax checks and all five library-logic tests: passing.
- Installed Python dependencies: `pip check` reports no broken requirements.
- Browser workflow: create a resource with tags, notes, and a favorite; search for it; mark it complete; edit notes; reload and verify persistence; remove the test resource and verify the filtered empty state.
- Visual check: desktop layout and a 390-pixel mobile viewport; light and dark themes; no horizontal overflow at the tested mobile width.
- Browser console: no errors or warnings observed in the completed check.
- Repository screenshot: captured from the real running app using optional demo data.

Browser QA used a separate temporary SQLite database. It did not populate the default library. Import/export behavior was tested through the API suite; the operating-system file picker was not automated. The GitHub Actions configuration has not been run on GitHub yet. Python versions other than 3.12 are configured in CI but were not locally executed.
