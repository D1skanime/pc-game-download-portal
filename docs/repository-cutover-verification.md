# Repository continuity evidence

The read-only verifier `backend/tools/phase38_cutover.py` checks a repository
rename and the final feature acceptance record. It does not collect evidence,
change a remote, push, rename a repository or operate services. Run it from the
canonical Linux checkout. Missing or unverifiable required evidence fails.

```sh
python3 backend/tools/phase38_cutover.py --before before.json --after after.json --validation validation.json
python3 -m unittest discover -s backend/tools/tests -p test_phase38_cutover.py -v
```

All three JSON documents use `schema: 1`. The before/after documents contain
`repository` (numeric `id`, `node_id`, `owner`, `name`, `default_branch`,
`visibility`, `description`, `homepage`), `origins` (`fetch`, `push`),
`refs`, `releases`, `issues`, `pull_requests` and `metadata_edits`.
Refs are sorted unique `[refname, object_id]` pairs from advertised heads/tags,
including separate `^{}` rows for annotated tags. Repository identity is fixed
to D1skanime's existing numeric ID 1415481891 and node ID R_kgDOVF6KIw.
The expected names are pc-game-download-portal before and zockarchive after,
with main as the public repository's default branch.

Capture all paginated releases, assets, issues and pull requests. Preserve their
full metadata, sorted by numeric ID; do not discard fields to conceal changes.
The minimum required content fields are enforced by `records()`. Asset content
must have a SHA256 digest; absent API digest requires downloaded-content evidence
before proceeding. Never alter historical bodies, titles or notes. Only explicit
URL keys receive own-repository URL-prefix normalization. Other repository
metadata remains identical except separately declared description/homepage edits:
`metadata_edits: {"description": [old_value, new_value]}`.

The before document additionally contains `repository_head`, `local_refs`
and `backup`. The latter contains `source`, `local_refs`, `mirror`,
`local` and `remote`. Each bundle has `path`, `sha256` and exact `refs`.
Backups must resolve inside `/home/d1sk/za-backups/phase38-cutover`, outside the
checkout, without symlink escapes. Both bundles must be self-contained, pass
Git verification and advertise the relevant source commit. The local bundle
covers HEAD and all local refs, including unpublished feature commits. The
remote bundle covers every advertised head/tag, with the mirror also proving
peeled tag objects and object integrity. Record later pushes separately; there
must be no ref-changing push during before/after comparison.

The validation document contains:

- `repository_id`, final `pr_head` and `final_source`.
- `backend`: exactly eight SQL-profile shards each for MariaDB and PostgreSQL, with
  `dialect`, `shard`, complete ordered `files`, `source`, `action`,
  `tests`, `failures`, `errors`, `skipped`, `passed`.
- `host_contracts`: the required complete-checkout job's artifact, with
  `schema: 1`, `repository_id`, `job: "host-contracts"`, `passed`,
  exact `source`, successful current-source `action`, prerequisite versions
  (`git`, `node`, `compose`), complete `membership` (`all`, `sql`, `host`)
  and sorted `file_results` (`file`, positive `tests`, zero `failures`,
  `errors`, `skipped`, and `passed`). All four required host suites must
  execute; source-manifest equality alone cannot replace their test results.
  The shared classifier partitions the complete tracked pytest selection, with
  no overlap or missing file. All16 SQL shards use only the SQL profile.
- `schema_gates`: MariaDB, MySQL and PostgreSQL, each with `source`, `passed`,
  zero `failures`/`skipped` and steps
  `["upgrade-head", "downgrade-base", "upgrade-head"]`.
- Nonempty `actions` entries with actual numeric `id`, `repository_id`,
  `head_sha`, canonical new-repository `url`, completed `status` and success
  `conclusion`. Every backend and required host run must appear in this inventory.
- `links` with one current HTTP 200 result per fixed `REQUIRED_LINKS` key:
  `kind`, `url`, `final_url`, `status`, `classification`, `source`.
  A redirect to another location does not establish current-link proof.
- Separate nonempty explanations for `artwork`, `physical_controller`,
  `native_desktop`, `registry`, `production_portainer` in `limitations`.
- `later_ref_changes` entries with `ref`, nullable `before`, `after` and
  `reason` (`feature-push` or `metadata-push`). An empty list is valid
  when no later ref changes occurred.

Each source proof contains `commit` and `manifest`. Use
`phase38_cutover_source.manifest(commit, domain)` to calculate the complete
fixed path/mode/blob map and SHA256 digest. The full domain includes every
tracked non-planning file. A CI merge checkout is accepted only when the final
head is its direct parent and the complete source maps match. Schema equivalence
uses fixed backend runtime/dependency/authority coverage and also requires
`observed_inputs`, the actual snapshot's code-before manifest with `files`
(path to content SHA256) and its original sorted-JSON `sha256`. Its runtime
projection must match independently hashed Git blob bytes. Do not synthesize
observations from Git or trust an `equivalent: true` flag.

Receipts are sanitized attestations, not a replacement for retaining and reading
the underlying Actions APIs, complete job/artifact results, JUnit, schema command
logs, snapshot manifests and HTTP observations. A missing original snapshot
manifest cannot be reconstructed into a claimed runtime observation. Rerun the
owned gate when it cannot be verified. No production acceptance or publication
is implied by a successful validator.
