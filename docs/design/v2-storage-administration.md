# RomM V2 Storage Administration Design Contract

## Table of Contents

1. Scope and authority
2. Route and entry convergence
3. Backend Contract
4. Mapped storage overview

## 1. Scope and authority

This document is the normative design contract for RomM v2 storage administration. The live FastAPI and OpenAPI contracts remain authoritative for data and error semantics.

This phase is documentation and design only. It does not implement Vue components, backend behavior, routes, generated types, dependencies, deployment, Phase 5 read-path work, or Phase 7 UI work. New UI work belongs to RomM v2. Frozen v1 is not a design target.

The external archive is read-only. RomM indexes source content without changing original files. The interface never reconstructs or displays a container, NAS, host, composed, or absolute location. Location presentation is only a friendly root name followed by server-authorized relative breadcrumbs. This resolves UI-01 in favor of D-08 and the live redacted schema.

## 2. Route and entry convergence

The canonical route is named `platform-storage-mapping` at `/platforms/:platformId/storage`. Platform detail and storage settings both navigate to this route with platform context. Settings may provide administration chrome, but not a second workflow or draft model. The route answers: "Where are this platform's games stored?" It requires authenticated administrator authority. Frontend permission gating is only a usability hint; backend authorization remains decisive.

| Entry | Context | Destination | Rule |
|---|---|---|---|
| Platform detail | `platformId` | `platform-storage-mapping` | Primary platform-led entry |
| Storage settings | chosen `platformId` | `platform-storage-mapping` | Converges after platform selection |
| Direct route | route `platformId` | Same view and model | Missing, forbidden, and invalid states remain bounded |

## 3. Backend Contract

The client renders only allowlisted response fields and never combines identifiers into technical locations. Unicode and case are preserved exactly in root names, directory names, and relative breadcrumbs.

| Concern | Authoritative fields and states | Presentation contract | Prohibited inference |
|---|---|---|---|
| Roots | `id`, `name`, `mode`, `active`, timestamps, `health` | Friendly name, immutable mode, activity, and independent health properties | No technical path from identity or deployment knowledge |
| Health | `reachable`, `readable`, `non_writable`, `checked_at`, bounded `error` | `true` confirms non-writable, `false` warns, and `null` means unknown or unconfirmed | No filesystem detail beyond the bounded message |
| Browse | `name`, `relative_path`, `navigable`, `next_cursor` | Relative breadcrumbs and paginated rows in server order; preserve Unicode and case | No absolute breadcrumb, guessed parent, or changed casing |
| Mapping | IDs, `relative_path`, `active`, `version` | Bind active mapping by identity and version; join only to an authorized friendly root | No silent fallback for a missing mapping |
| Fast test | draft identity and path, `valid: true`, or bounded error/conflict | Success qualifies the unchanged draft for save; failure stays local | No persisted test history or implied full scan |
| Conflicts | bounded `code`, allowlisted IDs, optional `current_version` | Explain overlap, duplicate, missing, or stale state without unrelated mapping detail | No disclosure from conflict context |
| Shallow preview | persisted identity/version, bounded counts, truncation, cursor | Immediate bounded directory summary, not recursive discovery | No total size or completeness claim when truncated |
| Queued preview | identity/version, health, `pending`, `partial`, `complete`, observed values, bounds, timestamp, problems, stale, bounded error | Start only after save; label lower bounds and ignore stale results for current mapping | No request against an unsaved draft |

Create uses the selected root and relative path. Change and removal submit `expected_version`. On `storage_mapping_stale_version`, retain the local draft, state that the mapping changed, and offer `Reload mapping` followed by explicit review. Never retry with a substituted version or discard edits without confirmation.

## 4. Mapped storage overview

Use one compact read-oriented summary with stable regions, not nested cards. Priority order is safety and reachability, mapped root and relative folder, latest persisted-mapping preview, mapping actions, then spatially separated removal. Safety has the strongest emphasis. The single primary action is `Map storage` when unmapped or `Change mapping` when mapped. Test and preview are secondary.

An existing mapping opens in overview mode. `Change mapping` opens a prefilled draft while the current mapping remains active. Removal is destructive, requires confirmation, and states that source files remain unchanged. Local refresh replaces only its affected region; the page heading, platform identity, breadcrumbs, and navigation stay mounted.