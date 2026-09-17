# Phase 16 Cross-platform Desktop UAT

This record is intentionally evidence-based. Host-only compilation does not
substitute for Windows, standard Linux, or Bazzite bundle/start evidence.

## Windows

- Status: `BLOCKED`
- Runner/version:
- Bundle filename and SHA-256:
- Installed/bundled start result:
- Focused core integration output:
- Sparse 30 GiB UAT result:
- Temporary UAT root removed: `NOT RUN`
- No Team4s/NAS/deployed-RomM access: `CONFIRMED BY TEST DESIGN`

## Standard Linux

- Status: `BLOCKED`
- Runner/version:
- Bundle filename and SHA-256:
- Bundled start result:
- Focused core integration output:
- Sparse 30 GiB UAT result:
- Temporary UAT root removed: `NOT RUN`
- No Team4s/NAS/deployed-RomM access: `CONFIRMED BY TEST DESIGN`

## Bazzite

- Status: `BLOCKED`
- Bazzite version/runner:
- Bundle filename and SHA-256:
- Installed/bundled start result:
- Focused core integration output:
- Sparse 30 GiB UAT result:
- Temporary UAT root removed: `NOT RUN`
- No Team4s/NAS/deployed-RomM access: `CONFIRMED BY TEST DESIGN`

## Sparse 30 GiB evidence schema

The ignored executable test must record these values for each authorized run:

| Field                     | Result   |
| ------------------------- | -------- |
| Source logical size       | `30 GiB` |
| Destination logical size  |          |
| Bytes before interruption |          |
| Resumed `Range` offset    |          |
| Exact `If-Match` snapshot |          |
| Final SHA-256             |          |
| Finalization result       |          |
| Temporary root cleanup    |          |
| No-NAS assertion          |          |

Phase 16 remains incomplete while any platform row or the isolated large-file
run is `BLOCKED`.
