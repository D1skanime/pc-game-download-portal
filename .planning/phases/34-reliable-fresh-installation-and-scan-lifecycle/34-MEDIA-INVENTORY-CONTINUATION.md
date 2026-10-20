# Phase 34 Inventory Continuation Decision

Date: 2026-10-19. Parent-owned bounded correction decision.

Group 3 remains open at 34-MEDIA-FIX-CATALOG.md. CR-02 and CR-08 have committed executor proof. CR-05 still fails a valid 1,000-output inventory with EMFILE, and two existing badge fatal controls remain red.

The accepted provider inventory contract already requires this cardinality. Releasing prepared descriptors is a necessary internal correction within CR-05, not a new feature, phase, storage authority or user-facing API. Continue with a bounded lifecycle extension of the existing PreparedOwnedFile authority and coherent extraction if needed to respect module limits.

Preparation, streaming, validation, hashing and durability happen outside SQL publication locks. A sealed output must release descriptor resources without losing exact staging ownership. Reacquisition must use existing no-follow capabilities, validate expected parent/file identity and unchanged bytes, preserve no-clobber publication and unknown-outcome semantics, and never unlink a substituted or foreign object. Failure and abort must remain safe before and after sealing.

No raising process file limits, truncating accepted inventories, increasing manifest bounds, duplicating resolvers, raw-path writers or partial catalog inventory commits. Retain bounded manifests, schema 1 compatibility, one atomic catalog association and the existing fatal publication seam. Preserve all original assertions.

Use the guarded disposable runner. Prove the accepted inventory with bounded descriptors, sealed-file/parent substitution negatives, cancellation/rollback/abort behavior and actual PostgreSQL publication/cleanup. Keep pgdp-dev stopped and host Media untouched. No dev database reset yet.

CR-09 and WR-02 from the independent recovery review remain a separate serialized follow-up. Original findings and evidence remain intact. This decision does not approve or close any quality gate. Parent owns shared tracking.
