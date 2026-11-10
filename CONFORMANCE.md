# Candidate profile conformance guide

This guide organizes acceptance checks for [SPEC.md](SPEC.md). The specification is normative;
this checklist does not add fields, defaults, execution permissions or a mandated test framework.
The profile remains a candidate. **Everything currently specified is core.** Conformance requires
the entire core specification, including the complete required yapyon baseline and its standard
functions; an implementation cannot choose a feature subset and claim conformance. The sections
below organize acceptance by operation, not independent partial-conformance classes. Optional
fields may be omitted in documents, but their defined semantics must be implemented.

Reports should identify exposed operations, resource/trust limits, tested revision and exact
boundaries exercised. A limited tool may describe its capabilities accurately without claiming
profile conformance. Valid core input rejected for missing implementation support is a conformance
defect, even when the error is explicit and no data is corrupted.

## 1. Registry reader

- Discovery selects one explicit/environment/XDG/home root. Relative roots use the invocation's
  working directory; an explicit empty root errors. A malformed selected root does not trigger fallback.
- Missing, empty and comments-only registries list an empty store without writing anything. A
  non-mapping, computed registry, unsupported marker or unknown fixed-schema field errors.
- An explicitly selected profile supplies an omitted marker. A multi-profile reader reports ambiguity
  instead of guessing an unmarked nonempty store's format. No `v0.1` alias or marker-only migration.
- Exact case-sensitive registered names survive save/reload. Invalid identifiers and lowercase
  `default` fail. Shell words such as `if` are valid storage names; launcher restrictions are separate.
- Registration paths are authoritative absolute paths. Changing `paths.entries` does not redirect a
  registration, and a directory with an agent-like name is not an unregistered fallback.
- Reject overlapping lexical registration paths and invalid records. Listing does not parse every
  agent, initialize a manager or fetch a credential.
- Validate all supplied defaults recursively against the specification's complete eligible field set,
  including absent-but-defined source fields. Reject identity/description and unknown specification
  keys; retain arbitrary keys within declared data-valued fields.
- Preserve explicit valid `None`, `[]`, `{}` and default-equal author settings in sparse writes. Check
  the nested environment policy and reserved discovery names without reading other environment values.

## 2. Source reader and resolver

### Source and dependencies

- Decode UTF-8 yapyon with the complete pinned language semantics permitted by the profile, including
  every standard built-in. Reject duplicate keys and calls outside the profile; do not reject valid
  core calls as optional unsupported features or return unresolved expressions as successful literals.
- Accept direct `agent` mappings and retained agent inheritance. Require one top-level agent branch,
  with no persisted `runtime` or `agent.path`.
- Look up `persona.local` only as `<configured-shared-root>/persona/local.tmpl`. Test a renamed
  relative root, an absolute root, one-segment and deeper labels, and an included file containing a
  nested include. A same-named decoy beneath the including directory must not change the result.
- Supply the loaded document's single literal branch value as the filler; do not reinterpret the
  filename label as a path inside the document or silently discard a computed branch key. Missing
  files/branches, cycles and unfilled slots error.
- Reusing a dependency twice is not a cycle. Finite depth/size/work limits must fail explicitly rather
  than loop, silently truncate or fall back to a changing application catalog.
- Follow permitted links; refuse dangling targets, link loops and non-regular document targets.
  No read creates directories, refreshes shared files or downloads a missing component.

### Defaults and binding

Test all three levels, not just the store's secret selector. At minimum:

| Store/source case | Required result |
|---|---|
| Store `context_size: 200000`, file omits it | `200000` |
| Same store, file `context_size: None` | `None` |
| Same store, reused file supplies `300000` | `300000`; the reused file is ordinary file source |
| Store model list is nonempty, file supplies `[]` | Authored `[]`; no default-list concatenation |
| Store native mapping is nonempty, file supplies `{}` | Authored empty native mapping |
| File `mind: {}` | Omitted record fields may receive defaults |
| File `mind:= {}` | No lower-record resurrection; required missing fields fail |
| Generic dialect verification headers, protocol-specific body | Both defaults apply unless source overrides/resets them |
| A protocol is `None` | It remains disabled; generic dialect defaults do not enable it |
| Omitted active/subagent model, authored model list | Fallbacks bind to the final list/active model |
| Registered name differs from authored name | Final name and derived secret entry use the registry name |

Explicit file-list/mapping composition must still use ordinary yapyon operators, including its
non-associative histories. These boundary fallback tests do not authorize replacing file composition
with dictionary update. Include deferred references, valid empty values, record resets, typed value
copies and source-save/reload under changed defaults in the checks.

### Typed definition and authentication

- Validate required and optional field types after binding. Reject booleans as context-size integers,
  malformed endpoints, bad environment names and a native filename that is absolute or contains `..`.
- Preferred-first enabled/supported protocol selection must be deterministic. An explicit compatible
  selection wins; an empty intersection or invalid explicit selection fails without a provider request.
- Keep disabled dialects, `None`, `False`, zero and empty native data in raw results. Explicit
  `__not_none__()` output-copy filtering may omit only what that authored transformation specifies.
- `secret: None` remains keyless when the default backend changes. Missing secret/default slots follow
  the current default. Explicit named/inline backends do not switch selection with that default.
- Root `None` means an unprefixed keyed entry. Explicit complete entry overrides are not prefixed again.
  A rename changes a derived entry but not a fixed entry or a record in a password manager.
- Neither keyless selection nor a selected backend authorizes rewriting `auth_var`, `env_key` or a
  matching native environment entry. Test deliberate wrapper/inherited authentication and explicit
  output-copy filtering independently.
- Every information-only path is exercised with manager/provider/install/launch boundaries trapped
  to fail if invoked. Successful parsing alone does not establish this property.

## 3. Writer

- Preserve deferred references, dependencies, replacement intent and source order. Compare resolved
  values after save/reload with both current and changed defaults/environment/registration inputs.
- Retained and faithfully composed source forms should agree in the same context. Label exports
  with unresolved dependencies as partial; label resolved exports as snapshots of explicit inputs.
- Refuse unrepresentable source before replacing files. Preserve unrelated registrations and settings.
- Test stale prepared candidates, missing/readonly targets, linked file writes and partial IO failures.
  Do not claim a cross-file transaction without implementing it.
- Refuse dangerous lexical agent destinations before writing. Removing a linked registered directory
  unlinks the directory entry, not its target. Agent removal never implicitly deletes credentials.

## 4. Credential consumer and installer/launcher

These are separate acceptance legs, not consequences of resolver conformance:

- Verify the selected backend's exact entry/argv, quoting and literal final-entry handling. Spaces,
  quotes and metacharacters remain data; no implicit shell, expansion or secret-bearing argv/logs.
- Document the consumer's credential encoding/normalization, environment and finite execution limits.
  Trap nonzero status, bad/empty output, missing manager and unknown state as distinct failures.
- Fetch uses stdout; store uses stdin. Nothing executes merely because source contains a command.
  Test with synthetic managers before any separately authorized real-manager operation.
- Validate generated files and wrapper refusal for shell-reserved command names. A native filename
  is relative to the fixed harness directory; no silent relocation or identity rename.
- State whether launch uses snapshots or current resolution. Editing shared source does not silently
  update installed native files/wrappers.
- Native-client acceptance, real credential lookup, provider response, kanibako consumption and Mojo
  parity each need their own recorded check. A fixture, file-generation test or release does not prove them.

## 5. Existing executable example

From any working directory:

```sh
nice -n 19 ~/.venvs/pg/bin/python -I ~/workspace/agent_store/validate_examples.py
```

That local venv path is a convenience; another interpreter with the pinned language semantics is
valid. `--help` documents the helper. The fixture uses an explicit synthetic environment, inert
manager names, fictional registry paths and no credentials. It never imports PG.

The current helper checks 49 bounded example cases. It covers actual resolved fixture values,
source persistence, selected validation/default-eligibility rules and configured/nested includes.
It **refuses generic default application**: the generic binding cases in §2 above must be tested
in the implementation, not reported as covered by this helper. It also does not establish the
full filesystem, type-validation, execution or native-client checklist. A green run is example
regression evidence, not a complete conformance certificate or approval of the standard.
