# agent_store

An interoperable on-disk format for independently named agents composed from a persona, a harness
and an optional credential-backend selection.

**Candidate profile: `agents-yapyon-v0.6.5`.** The documentation is a complete proposal, not a claim
of final adoption, PG conformance or successful native/provider integration.

- [Specification](SPEC.md): normative language revision, discovery, registry/schema, complete defaults
  and binding rules, shared-root includes, persistence, credentials, extensions and failure boundaries.
- [Conformance guide](CONFORMANCE.md): role-specific acceptance cases and limits of the example checker.
- [Examples](examples/README.md): synthetic `shared/` and `entries/` fixture, including keyless,
  unprefixed and default-backend agents; the checker runs offline without PG or credentials.
- [AI contribution policy](AIPOLICY.md).
- `sample/`: protected historical input, not a current-profile baseline or migration source.

The language baseline is yapyon 0.6.5 at the immutable revision linked in the specification.
Model IDs, providers and native harness formats are not defined by this store format. Reading a
store does not authorize credential retrieval, provider requests, native installation or launch.

PG implementation is maintained separately. Any migration of existing `agents-yapyon-v0.1` stores
is a separate operation.
The two markers are not aliases; changing one is not a migration.
