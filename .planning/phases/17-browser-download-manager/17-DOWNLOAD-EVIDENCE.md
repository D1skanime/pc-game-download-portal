# Phase 17 Isolated Download Evidence

**Recorded:** 2026-09-24

All observations below used the isolated UAT stack at `127.0.0.1:3344` and
the read-only temporary source root. No real NAS or Team4s source was used.

| Case                          | Result | Evidence                                                                                                                                                                                                                          |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Large single ISO              | PASS   | A 5 GiB ISO was transferred with Enhanced mode. Source and destination SHA-256 were identical: `7f06c62352aebd8125b2a1841e2b9e1ffcbed602f381c3dcb3200200e383d1d5`. The fixture was removed after the test to preserve disk space. |
| Multi-file game               | PASS   | Forty DLC ZIP members completed through the Enhanced queue with bounded concurrency.                                                                                                                                              |
| Update-only selection         | PASS   | The immutable manifest contained exactly three update ZIPs, 49,152 bytes total, and no main-game member. Standard mode recorded all three as `served`.                                                                            |
| DLC-only selection            | PASS   | A 40-member DLC-only manifest was created and handed to the browser without main-game members.                                                                                                                                    |
| Pause and resume              | PASS   | A 2 GiB Enhanced ISO was paused at 1,738,539,008 bytes, resumed with `Range` plus `If-Match`, received `206`, and completed byte-identically.                                                                                     |
| Source change                 | PASS   | Replacing one source byte between pause and resume produced `412` and the transfer entered `source_changed`; old and new data were not combined.                                                                                  |
| Standard multi-file safeguard | PASS   | Chromium served 19 files then applied its own automatic-download restriction to the remaining handoffs. RomM respected this browser decision and did not claim local persistence.                                                 |
| History and transfer controls | PASS   | Cancel, per-entry removal, remove-all, retry and standard-status reconciliation were exercised in the live UI.                                                                                                                    |

## Source safety

- The source root was mounted read-only in the application container.
- Direct files were streamed; no server ZIP, staging copy, split archive
  assembly, rename, or source-root sidecar was created.
- The 5 GiB source and downloaded destination hashes matched exactly.
- Test fixtures and local destinations were removed only after evidence was
  collected.

## Automated verification note

Focused frontend tests, typechecking, production build, and file-scoped Trunk
checks passed during implementation. The checkout's standalone pytest fixture
still cannot reach its configured `127.0.0.1:3306` test database. This does not
invalidate the live isolated MariaDB-backed UAT above, but remains an
environmental limitation of the host test command.
