# Phase 17 Browser Download Matrix

**Recorded:** 2026-09-24

## Scope decision

The product owner accepted Chromium as the live browser UAT target and explicitly
waived Firefox and Edge execution for this phase. A waived browser is not a
cross-browser compatibility claim.

## Results

| Browser                           | Standard download                                           | Enhanced folder download                                                         | Multi-file behavior                                                                                                              | Range/resume                                                                | Directory API                                    |
| --------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------ |
| Chromium 153 (isolated Linux UAT) | PASS: attachment handoff and server `served` state observed | PASS: native directory picker, streamed writes and SHA-256 verification observed | PASS: 40-file enhanced queue completed. Standard handoff stopped after Chromium's automatic-download limit without bypassing it. | PASS: 2 GiB pause/resume returned `206`; source replacement returned `412`. | Available and used through capability detection. |
| Firefox                           | WAIVED by product owner                                     | WAIVED                                                                           | WAIVED                                                                                                                           | WAIVED                                                                      | Not claimed.                                     |
| Edge                              | WAIVED by product owner                                     | WAIVED                                                                           | WAIVED                                                                                                                           | WAIVED                                                                      | Not claimed.                                     |

## Browser safety observations

- Standard mode remained available independently of the directory API.
- Chromium automatic multi-download restrictions were respected. RomM did not
  attempt to change browser permissions or bypass the browser safeguard.
- Enhanced mode used a user-selected directory and streamed response bytes to
  `FileSystemWritableFileStream`; it did not buffer the 5 GiB fixture as a
  Blob or ArrayBuffer.
