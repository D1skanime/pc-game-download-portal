# Phase 34 Inventory Content-Proof Design Checkpoint

Date: 2026-10-19. Status: user decision required before changing the technical publication contract.

## Preserved execution result

CR-05 remains open. Read 34-MEDIA-FIX-INVENTORY.md at 82dd26fd1 and the earlier catalog checkpoint at 5cf542a65. The draft handles the valid 1,000-image inventory and the original badge fatal controls with bounded descriptors. The final compatibility run is 81 passed and two failed out of 83, including all 64 existing storage cases.

Same-inode content modification can retain identical size, mtime and ctime on this actual Linux 5.15 host. Metadata-only sealed ownership checks therefore do not establish unchanged bytes. The modified-private abort and recovery cases remain red. An earlier publication rejection pass was timing-dependent, not proof.

The runtime drafts and all assertions are preserved. No corrective GREEN, new SUMMARY or phase acceptance exists. Test RED commit e0491bf0e and additive checkpoint commit 82dd26fd1 resolve.

## Contract boundary

The approved plan requires hashing, streaming and validation outside SQL publication locks, bounded descriptors, exact cleanup and one fenced inventory association. A fresh pre-lock hash followed only by metadata rechecks does not itself prove unchanged content across the final boundary on this host.

Do not weaken assertions, assume inode/timestamps are a digest, raise file limits, truncate valid inventories, add unverified notification hints, or invent a privileged/filesystem-specific sealing dependency.

A targeted plan revision is proposed to evaluate bounded final content verification at the fenced publication boundary, with an explicit deadline, safe failure, retained prior media and no late verifier writes. This would change the technical no-hashing-under-SQL-lock rule. It requires a planning decision and feasibility review before implementation. Do not claim that a deadline mechanism or implementation is already proven.

The guarantee must be explicit about application-owned mutation authority. Arbitrary privileged host filesystem modification can also corrupt files after publication and cannot be silently promised away.

## Other open findings

The independent catalog-lock review, 34-MEDIA-FIX-CATALOG-LOCKS-REVIEW.md, reports CR-10: reused-session stale provider JSON can overwrite newer references. CR-08 has no additional review finding.

The independent recovery review remains open for CR-09, Alpine libc binding incompatibility, and WR-02, crash-left PID-named cursor temporary collision. Its report is committed at c0a0d4f27.

Group 1 CR-01/06/07 remains independently clean. Original findings and all additive evidence remain intact. Five summaries do not establish Phase 34 acceptance. Phase 33 acceptance stays open.

## Environment and resume

The user approved stopping pgdp-dev and later rebuilding the dev database for fresh UAT. The app remains exited with running=false; DB and Valkey remain running. No dev database reset, Media deletion or Games mutation was performed. Preserve the two host Media control files and all unrelated dirty work.

All subagents are closed. Completed test runs report exact cleanup and unchanged sources. No further implementation, test or restart is scheduled pending this design decision.

After approval, use the canonical Linux preflight, targeted GSD planning/review for this publication constraint, then corrective execution with real SQL/filesystem/timeout and full regression evidence. Continue CR-10 and recovery compatibility fixes, independent review and remaining plans. Parent owns STATE, ROADMAP and requirement completion.
