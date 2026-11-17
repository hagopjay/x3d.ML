# Independent integration review

Read-only review of the figure-link adapter, its tests, the one-line private
`x3dprov` repair and tests, the evidence inventory adapter and its delivered
support queries. No bound source, receipt or graph file was edited by this
review. In-memory controls were run with bytecode writes disabled.

## Must address: noncanonical existing provenance can bypass append refusal

The initial `append_verified()` implementation accepts both `no-record` and
`verified` from the legacy protocol. `read_steps()` recognizes a deliberately
narrow textual serialization, requiring `name` before `content`. Well-formed
XML permits attributes in either order.

A fresh in-memory control performed these steps:

1. Stamp the adapter test's owned Box fixture with the existing protocol.
2. Change the existing step meta to `<meta content="…" name="x3dprov.step.1"/>`.
3. Change the Box from `1 2 3` to `1 2 4`.
4. Call the initial `append_verified()` with a new operation.

The legacy verifier reports `no-record` before append. The initial adapter
accepts it, returns a `verified` one-step chain, and the resulting XML contains
**two** `x3dprov.step.1` meta elements: an invisible old record and a new record.
Thus the guard's broad claim to refuse stale or broken existing input requires
one more structural check.

Recommended narrow fix: an unstamped initialization may contain no
`x3dprov.*` head metadata; if any such metadata exists, require a verified,
recognized record and compare parsed step markers to the protocol's recognized
step list. Reject unsupported serialization and duplicate/unknown markers
rather than treating them as a fresh scene. A paired reordered-attribute control
is valuable. This concerns the reusable append API; the three current links
start from genuinely unstamped owned exports, so the finding does not by itself
invalidate their already delivered geometry/image bindings.

The finding and reproducer were sent to the parent for correction before final
packaging. This note records the reviewed initial state; consult the final
adapter tests and source identity for its resolution.

## Nonblocking future invariant: reproduction must retain structured scope

`inventory.validate()` requires a reproduced EvidenceRecord to reference a
different recorded run with matching subjects and contained facets. It does
not currently compare `scope_terms` between the original and reproduced
records. A future record could label a new saved frame as a reproduction of a
different frame while sharing the same Dataset and geometry facet.

The delivered inventory does not use the `reproduced` state, so this is a future
schema/policy improvement rather than a false current support result. Require
the repeated scope to match, or explicitly model the relation as a new scoped
execution instead of reproduction. Independent provenance or operator identity
would be a separate stronger policy; different run IDs alone do not establish
experimental independence.

## Checks that look correct

- The private core repair uses a replacement callback, preserving JSON newline,
  Windows-path and regex-like backslash sequences. It reuses the known archived
  correction without changing the protocol's hash method or public behavior.
  The five regression tests exercise literal data and repeated chain append.
- The adapter keeps the original packet-frame canonical hash separate from the
  exchange-normalized frame hash. Render receipts bind to the former; exported
  X3D metadata binds to the latter. The sidecar names both methods separately.
- XML content hash, exact file SHA-256, decoded scientific frame identity and
  PNG identity have distinct fields. Retrospective render linkage is explicitly
  `render_reexecuted: false`; it does not pretend to be a new rendering run.
- Bound artifact paths are resolved and constrained to explicit roots.
  Current local bytes and producer sources are checked independently.
- Support queries apply explicit subjects, facets and structured scope terms.
  Reading a prior passing receipt retains its recorded execution state while
  the inspection reports `fresh_execution: false`.
- All 23 delivered Claim queries were inspected against the delivered
  inspection. Six native-browser/post-edit-science controls and the historical
  corpus-count control remain unsupported; the 16 scoped recorded claims are
  supported. No geometry claim leaked into pixel parity or new scientific
  certification in those queries.

The inspected graph contains 238 Artifact nodes, 27 Bridge nodes, 27
EvidenceRecords, 26 ValidationRuns, 23 Claims, 18 ToolBuilds, 12 Datasets, 12
Losses, two CoordinateFrames and one Transformation. These counts describe the
inventory structure, not a count of newly reproduced experiments.


## Resolution in this delivery

The owning pass addressed both findings before packaging. The figure adapter compares parsed XML provenance markers with the legacy reader and refuses reordered, unknown or misplaced records; eight adapter tests pass. Its append helper is restricted to linking unchanged scene content. The inventory validator now requires matching structured scope terms for a reproduced record; the additional different-frame control raises the suite to thirteen tests. Original archived sources remain unchanged; the separate core callback repair is proposed as a private patch.
