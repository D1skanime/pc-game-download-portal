---
status: complete
---

# Resume expiry feedback summary

The enhanced resume flow now loads and validates the immutable manifest before
it creates a replacement session or cancels the prior active session. The UI
reports an expired manifest as an actionable restart requirement instead of
silently doing nothing after directory selection.

Live UAT against 3344 confirmed that deleting an individual terminal history
item returns HTTP 204 and immediately decreases the visible row count.
