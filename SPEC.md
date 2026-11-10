# agent_store — candidate specification

**DRAFT 0.6.5 — revised 2026-11-09.**

Settled review decisions are incorporated below: specification defaults are overridden by
store-config defaults, which are overridden by file settings. Reused files have no special
precedence tier. There is no automatic clearing of authentication references for a keyless selection
or generic keyed native-placeholder deletion. This remains a draft, not final adoption.

This document proposes an interoperable on-disk store for named agents. `persona_grata` (PG)
is the reference implementation, not the definition of the format. This draft describes a
candidate `agents-yapyon-v0.6.5` profile; released PG 0.0.7 writes `agents-yapyon-v0.1`.
The markers are not aliases. No migration, backward-compatibility claim or release is implied.

“MUST”, “MUST NOT”, “SHOULD” and “MAY” describe requirements **if this draft is adopted**.
Precise choices in this document are proposals, not claims that the maintainer previously
ruled on every detail. Adoption and reference-implementation changes require separate review.

## 1. Scope and terms

An **agent** is an independently named composition of one persona, one harness and an
optional credential-backend selection. Different agents may use the same persona/harness pair.
A **persona** describes cognitive configuration, including an endpoint and models. A **harness**
describes the client and its native configuration. A **dialect** describes a protocol's endpoint
mounts. A **secret component** describes a credential locator and manager operations, not the key.

A **store root** holds a registry and shared, in-use component definitions. An **agent directory**
holds one agent's persisted source and, optionally, generated native files. Agent directories
may live outside the store root. An agent's registered name, directory and component identifiers
are distinct concepts.

**Source** is unfinished yapyon, including references, slots and composition operations.
A **resolved definition** is a typed value obtained from source, its dependencies and explicit
runtime inputs. A **native snapshot** is output generated from a resolved definition for a
particular harness. These are different artifacts; none silently substitutes for another.

This specification defines discovery, source interpretation, data shapes and failure boundaries.
It does not standardize a CLI, shell-function name, manager setup wizard, package catalog,
provider probe, installation transaction, process supervisor or wire/API protocol. The conventional
discovery and command-splitting profile is POSIX-oriented; native Windows launch/path interoperability
is not claimed. An implementation
may expose those facilities separately. No executable named `pg` is required to read a store.

## 2. Format and conformance

### 2.1 Serialization

Files are UTF-8 yapyon. `.cfg` and `.tmpl` identify roles, not different languages. The language
baseline is yapyon 0.6.5 semantics: named/abstract slots, lexical references, typed value copies,
conditional expressions, ordinary composition, explicit replacement and unfinished-source saving.
An implementation need not use the Python yapyon package, but MUST implement the complete language
baseline permitted by this profile, including every standard built-in. Required language features
are not implementation-selectable options. The normative language references are the [yapyon specification](https://github.com/doctorjei/yapyon/blob/edce455fa28aff0a6b1752cdb07d00a7efe2f1e6/docs/SPEC.md)
and [grammar](https://github.com/doctorjei/yapyon/blob/edce455fa28aff0a6b1752cdb07d00a7efe2f1e6/docs/GRAMMAR.md)
at commit `edce455fa28aff0a6b1752cdb07d00a7efe2f1e6` (release tag `0.6.5`,
[package 0.6.5](https://pypi.org/project/yapyon/0.6.5/)). These immutable documents, not their
main-branch counterparts, define the language baseline. Later package versions do not by
themselves change this store profile. This document defines the store adapter and schema;
it does not redefine yapyon's expression, merge or slot-fill semantics.

The registry is a **record**: literal mappings, lists and scalars only. It MUST NOT evaluate
references, environment holes, slots, comprehensions or user-defined functions. Agent and
component documents may be templates. The base profile has no externally provided function
contract, Python imports or ambient application objects. Yapyon's specified built-ins, including
serializers, casts, `__get__`, `__env__` and `__not_none__`, retain their pinned language semantics.
Syntax or functions outside this profile are errors, not literal strings or instructions to execute
host code. Failure to implement a function or construct within the required baseline is an
implementation defect, not a reason to classify valid source as unsupported by the standard.
Profile fields called mappings require ordinary string-keyed mappings, not multimaps; a multimap
or another yapyon type may occur in free-form native/additional data where that data contract permits it.
Duplicate keys follow the language's errors; a reader MUST NOT silently choose a winner within
one mapping contribution.

Booleans are `True` and `False`; the absent-value literal is `None`. Strings MUST be quoted.
Plain `"$HOME/agents"` is text, not environment expansion. A reference such as
`y"{$HOME}/agents"` reads an explicitly permitted environment value.

### 2.2 Roles

Implementations SHOULD identify their supported roles:

- A **registry reader** discovers a store and reads validated names, locations and settings.
- A **source reader** additionally retrieves source and its dependency references without resolving it.
- A **definition resolver** produces and validates a complete definition under explicit runtime inputs.
- A **writer** persists source or registration changes without freezing deferred values.
- A **credential consumer** explicitly executes the selected backend's operations.
- An **installer/launcher** uses definitions or native snapshots to configure or start a harness.

A registry reader need not evaluate agent source. A source reader MUST NOT present an unfinished
document as a validated resolved definition. A resolver need not install or launch anything.
Roles describe capabilities and operation boundaries; they are not partial-conformance classes.
Conformance is to the complete core specification, not an implementation-selected subset. **Every
feature defined by this version is core.** An implementation MUST NOT claim conformance while
omitting any required core behavior, including support for well-formed standard-yapyon documents
using the core elements and satisfying this profile's schema and input requirements. An optional
field may be absent from a document; supporting its defined values and semantics is not optional.

A tool may accurately describe a limited capability, such as reading the literal registry only,
but that description is not a claim of conformance to this profile. Missing implementation support
for valid core input MUST be identified as an implementation deficiency, not a permitted feature
opt-out. Explicit input/context, IO, resource and trust-policy failures defined elsewhere remain
errors; they MUST NOT be used to disguise missing core support. This does not require executing an
unrequested operation or implementing a particular CLI or other facility outside §1's scope.

### 2.3 Version identification

The registry's `format` and resolved `agent.format` MUST equal `"agents-yapyon-v0.6.5"` for this
candidate profile. A present different marker is unsupported, even if its spelling looks older,
newer or related. Do not interpret a marker as a yapyon package-version requirement.

An absent, zero-length or comments-only registry describes an empty store with the baseline
defaults in §4. In a reader explicitly selecting this profile, an omitted registry `format` also
inherits the profile baseline. A multi-profile reader MUST NOT guess which profile an unmarked
nonempty store meant; it must obtain an explicit profile selection or report ambiguity. Writers
SHOULD include the marker in new nonempty registries. Agent source may obtain its format through
writer-side composition; if entirely absent, the selected profile supplies it before final validation. A present
wrong marker is never repaired by filling a default. A present agent marker must be a literal
string in the composed source, not a computed expression whose profile is learned only after evaluation.

A writer MUST NOT change a marker as a substitute for migration. Future incompatible semantics
require a different marker and an explicit compatibility policy. No ordering or automatic upgrade
relation is defined between `v0.1` and this candidate `v0.6.5`.

## 3. Discovery, identity and layout

### 3.1 Store discovery

Unless the caller selects a root explicitly, select the first nonempty value below:

1. `AGENT_STORE_DIR`.
2. `XDG_CONFIG_HOME`, with `/agents` appended.
3. The current user's home directory, with `/.config/agents` appended.

An explicit empty path is an error, not permission to fall through. Empty environment values are
unset for discovery. Expand a leading home shorthand (`~` or `~/`) in a selected path. Resolve a
relative selected root against the invocation's working directory, including a root selected
through `AGENT_STORE_DIR` or `XDG_CONFIG_HOME`. Callers SHOULD supply an absolute `XDG_CONFIG_HOME`
as the XDG convention requires; this profile defines relative input rather than silently selecting
a different store. No general shell-variable, wildcard or command expansion applies to path strings.

Select one root once per operation. Do not merge stores or search another root when a selected
store is malformed or an agent is missing. Read-only operations MUST NOT create directories or
materialize defaults. A missing root is an empty store for registry listing; resolving a requested
agent then fails as not registered. Path expansion and filesystem link traversal MUST NOT turn a
read-only request into a filesystem mutation.

`HOME`, `XDG_CONFIG_HOME` and `AGENT_STORE_DIR` are reserved readable environment names, both
for discovery and source expressions. An empty `env_vars.from_host` cannot hide them; §4 defines the full
expression-access set. A caller requiring stricter isolation must refuse access explicitly.

### 3.2 Identifiers

Agent names and component IDs use `[A-Za-z_][A-Za-z0-9_]{0,63}`; `default` is reserved. Names MUST
be nonempty and MUST NOT contain path separators. There is no derivation of identity from an
agent directory's basename or from a persona/harness pair.

The spelling of the registry name is the agent's public name. For registered-agent resolution,
the registry selection overrides the source's `agent.name` before expression evaluation; the
resolved name MUST agree with that selection. This binding is not a source rewrite or rename.
Writers SHOULD use quoted registry keys to preserve spelling. Names are case-sensitive string
values; readers MUST distinguish them from yapyon's normalized name-key lookup. Source field
names remain yapyon name keys so dotted references retain their language-defined meaning.
Component references follow yapyon's name-key semantics; writers SHOULD use lowercase component
IDs, and implementations MUST NOT substitute host-filesystem case guessing for those semantics.
For the permitted ASCII include segments, preserve case: `persona.Local` and `persona.local`
are different labels. A component's descriptive `name` is a nonempty string, not an instruction
to relocate that component or derive its include label. The identifier restrictions apply to
registered agent names, backend selectors and include-label segments, not opaque model IDs,
protocol names or descriptive component names.
A launcher may additionally refuse command names reserved by its shell; that is not a new on-disk
identity or permission to rename an agent silently.

### 3.3 Conventional layout

```text
<store-root>/
  agent_store.cfg
  shared/                              # configurable include root
    agent/shared_base.tmpl
    persona/local.tmpl
    harness/example_client.tmpl
    dialect/chat.tmpl
    secret/example_secret.tmpl
    secret/alternate_secret.tmpl
  entries/                             # configurable conventional entry container
    <creation-name>/
      agent.cfg
      harness/                          # optional native snapshot/state
```

`paths.shared` defaults to `"shared"`; `paths.entries` defaults to `"entries"`. They may be omitted
from the store config. Relative configured paths are anchored at the selected store root, not the
invocation's working directory or an including file. Absolute configured paths identify their
selected locations directly. Directory labels are locations, not identities or precedence levels.
The dotted namespace beneath the shared root is part of the include lookup contract (§5).

`agent_store-defaults.cfg` is a distribution artifact specifying a baseline, not a second
mandatory file every store must copy or an implicit extra local overlay. Readers MUST implement
the profile defaults even when the application is not PG. An implementation may distribute that
baseline as data, as the protected `sample/agent_store-defaults.cfg` illustrates.

Each registry agent record contains an absolute directory path without `..` segments. No
environment expansion or relative-path rebasing applies to a registry path. Source is
`<registered-path>/agent.cfg`. Only registered agents are visible; scanning the entries directory
is not an alternative registry. An explicit registered path remains authoritative even when it
is not beneath `paths.entries`; changing that default MUST NOT silently redirect registrations.
Equal or ancestor/descendant registered paths are invalid when compared lexically after ordinary
path normalization. That check does not prove distinct symlink targets.

A directory named `entries/old_name` can remain the directory of a renamed agent. Several agents
may share source; writers SHOULD NOT register the same physical agent source under conflicting
names. A reader MUST validate the requested record rather than rewrite another registration.
Writers MUST refuse an agent destination equal to the store root, selected entries/include roots,
the user's home or filesystem root, an ancestor of the store, or a child of the shared include
root. These lexical guards do not impose containment beneath `paths.entries` or a blanket symlink ban.

### 3.4 Filesystem links

Symlinks are permitted for the root, registered directories and files. A reader follows normal
filesystem resolution subject to caller permissions and explicit resource/trust policy. A path
outside the root is not intrinsically invalid. Missing targets and link loops are path errors.
Document targets must be regular readable files; readers MUST refuse devices, directories and
pipes rather than block indefinitely. Readers may impose finite document-size limits with explicit
resource-limit errors; no common 8 MiB limit is required by the profile.

Permission to read a link is not permission to recursively delete its target. Removing a registered
directory that is itself a symlink MUST unlink that directory entry, not recursively remove the
linked directory. A writer replacing a linked file MUST preserve the link relationship or refuse
before writing; it MUST NOT silently replace the link with an unrelated regular file.

## 4. Registry and defaults

### 4.1 Registry fields

The root is a literal mapping with these fields:

| Field | Type | Default / meaning |
|---|---|---|
| `format` | string | Profile marker, inherited if omitted under §2.3 |
| `agents` | mapping | `{}`; registered name to agent record |
| `defaults` | mapping | Nested entity defaults below |
| `paths` | mapping | `shared: "shared"`, `entries: "entries"` |
| `env_vars` | mapping | Host-environment access settings below |

`paths.shared` and `paths.entries` are nonempty path strings. The paths mapping has those two
fields; unknown path-setting names are errors. Omitted values inherit their specification defaults.
The entries path supplies a conventional location, not a rewrite rule for explicit registrations.

`env_vars.from_host` is the list of readable host-environment names (baseline below), and
`env_vars.additions` is an additional list of readable names, default `[]`. These are variable names,
not value assignments. The nested env_vars mapping has those two settings. This draft uses the
new names, not compatibility aliases for the former flat env_allow/env_add fields.

An agent record has only `path` (required, nonempty absolute directory string). Other fields at
these fixed-schema boundaries are errors. A registry MUST NOT contain credentials. An empty
scalar, list or non-mapping document is not an empty registry. Environment names must match
`[A-Za-z_][A-Za-z0-9_]*`; these lists contain names, not variable assignments or values.

There are specification defaults and user defaults. User-wide defaults belong in the `defaults`
mapping of `agent_store.cfg`; neither kind must be copied into each individual entity document.
Files may explicitly reuse other files through ordinary composition (§5); that reuse adds no
defaults source or precedence tier.

`defaults` accepts mappings for `persona`, `harness`, `dialect` and `secret`. Each group may set
sensible reusable fields defined by this specification, including their subfields recursively.
An omitted source field is eligible for a default; it need not already occur literally in the
agent/component document. An unknown specification field is an error, even if an application has
invented a same-named extension in its own component data.

Highly individual-entity-specific identity/description fields, such as a persona's, harness's,
dialect's or secret backend's `name`/`desc`, MUST NOT be supplied through user-wide defaults.
Those fields remain valid in the actual entities where defined. This is a semantic restriction
on entity identity, not a blanket ban on a data key spelled `name` inside free-form native data.
Other reusable specification fields are eligible. Spec-defined free-form/data mappings retain
their declared value contract; their data keys do not become new specification field names.

There is no `defaults.agent` group: its direct identity/description fields are individual-specific,
and the reusable groups are addressed under their own names. `runtime` is not user-defaultable.
Identity-independent baseline values are supplied by the specification; optional descriptive
fallbacks expressed in source do not make entity identity a user-wide defaults setting.

The store-level secret selector and initial baseline include:

| Field | Type | Specification default |
|---|---|---|
| `defaults.secret.backend` | component-ID string or `None` | `None` |
| `defaults.secret.root` | manager-relative root string or `None` | `"agents"` |

For the store's backend selector, `"example_secret"` selects the normal include label
`secret.example_secret`, hence `<shared-root>/secret/example_secret.tmpl`. An explicitly authored
named slot uses its complete qualified label. The selector does not add a different search root.

This table does not limit secret defaults to those two settings: eligible `entry`, `fetch`, `store`,
`probe` and `check` settings are also in scope, as are specification-defined persona/harness/dialect
settings. Backend selection is distinct from the selected backend's own entity name. `None` for
the whole defaults/group mapping is not shorthand for clearing it. Backend `None` means no default
backend; root `None` means no prefix and does **not** mean keyless.

### 4.2 Defaults cascade

Precedence, lowest to highest, is:

1. **Specification defaults.**
2. **Store-config defaults**, overriding specification defaults.
3. **File settings**, overriding the applicable defaults.

A value supplied by an explicitly incorporated file is a file setting, even if that file is
informally called a base or reused by many other files. The format gives no file a special
base/default status. File settings do not lose their precedence merely because they came from
another file in the collapse. Applicable defaults are lower contributions to ordinary yapyon
composition: `:` combines compatible values and `:=` replaces the complete field, including lists
and native mappings. There is no implicit whole-value replacement exception at the defaults/source
boundary. Omitted fields can inherit defaults; supplied fields follow their authored operators.

Across the defaults/source boundary and within the file layer, ordinary yapyon composition order
and operators apply. Do not introduce a separate base-file tier or filename-dependent merge/override rule. Preserve
explicit `None`, empty values and replacement intent; a present valid value is not omission.
Apply contributions while source is still deferred and resolve references in their final assembled
scope. A reader must not freeze agent-bound expressions early merely to construct defaults.
Registry listing does not resolve an agent or evaluate its source-bound values. PG 0.0.7's
secret-only default binding is not the complete standard.

### 4.3 Effective registry settings

Overlay explicit registry settings on the profile baseline **field by field for schema-record mappings**.
Data-valued fields identified in §4.4 use the whole authored value in this literal-registry overlay.
Lists, including `env_vars.from_host`, replace baseline lists; they are not ordinary yapyon source-list
merges. Registry processing consumes literal record values (`loads_record` semantics), not source-merge
operations; it need not preserve registry operator annotations. This is separate from applying effective
entity defaults to source under §§4.2 and 4.5, and does not turn the registry into a template or evaluator.
Omitted fields inherit. Explicit `None` where permitted, `[]`, `{}` and values equal to a baseline are
authored values, not evidence of omission. A sparse write MUST preserve their intent instead of deleting
them because they happen to equal today's default.

The baseline environment settings are:

```yapyon
env_vars:
  from_host: ["COLUMNS", "DATEMSK", "HOME", "LANG", "LANGUAGE", "LC_ALL", "LC_COLLATE",
    "LC_CTYPE", "LC_MESSAGES", "LC_MONETARY", "LC_NUMERIC", "LC_TIME", "LINES", "LOGNAME",
    "MSGVERB", "NLSPATH", "PATH", "PWD", "SHELL", "TERM", "TEXTDOMAIN", "TEXTDOMAINDIR",
    "TMPDIR", "TZ", "XDG_CACHE_HOME", "XDG_CONFIG_DIRS", "XDG_CONFIG_HOME", "XDG_DATA_DIRS",
    "XDG_DATA_HOME", "XDG_RUNTIME_DIR", "XDG_STATE_HOME"]
  additions: []
```

The source environment view contains the union of reserved discovery names (§3.1), effective
`env_vars.from_host` and `env_vars.additions`, filtered from a single caller-provided environment snapshot. Other
values are not readable. The
allowlist grants permission, not a value: an allowed-but-missing variable still follows yapyon's
missing-reference error rules. An agent document MUST NOT expand its own access policy. The
source environment is not automatically the environment exported to a launched process.

A stricter caller security policy may refuse an environment access or the operation. It MUST
report that refusal rather than silently supplying a fabricated or empty value.

### 4.4 Complete default-eligibility contract

The following is the complete recursive field set for user defaults. A path names a schema
field, not a requirement that it already occur in an entity's source. Its value has the same
type and context-independent constraints as the corresponding field in §§6–7; constraints needing
an agent path, other fields or protocol compatibility are checked on the bound definition. A defaults mapping may be partial:
required entity fields are required only after binding the selected definition. Invalid supplied
default values are registry errors even if no current agent uses them.

| Group | Eligible fields |
|---|---|
| `persona` | `mind.endpoint`, `mind.context_size`, `mind.model_list`, `mind.model_active`, `mind.model_subagent`, `mind.dialects` |
| `harness` | `path`, `auth_var`, `path_var`, `wrapper_env`, `config_file`, `config_store`, `content`, `supported_dialects`, `protocol` |
| `dialect` | `api_uri`, `msg_uri`, `model_uri`, `emb_uri`, `verify.check_uri`, `verify.key_header`, `verify.headers`, `verify.body` |
| `secret` | `backend` (store selector only), `root`, `entry`, `fetch`, `store`, `probe`, `check` |

`mind`, `verify` and individual enabled dialect definitions are schema-record mappings. A whole
`verify: None` is also valid and blocks defaults beneath that field. `mind.dialects` is a mapping
from exact, nonempty protocol strings to `None` or partial dialect records; those records have
the same recursive eligibility as `defaults.dialect`. A `None` protocol entry disables it and
MUST NOT be re-enabled by a generic dialect default. Generic `defaults.dialect` applies only to
enabled dialect records; it does not create protocols. Within the store-default level, per-protocol
values in `defaults.persona.mind.dialects` override generic `defaults.dialect` values. File settings
are higher than both. A default alone cannot supply an entity's identity: any resulting enabled
dialect must still obtain its required `name` from source.

`wrapper_env` and `config_store` are **data-valued fields**, not schema-record subtrees. The former
contains environment-name/string pairs; the latter contains arbitrary native data. Their keys do
not become specification fields, and a native `name` or `desc` is permitted. At a defaults boundary,
a supplied data value is used whole, including `{}`; a default is not spliced into an authored native
mapping. Lists and other non-record fields are likewise whole values at this boundary. This does
not change ordinary yapyon merging between explicitly composed files.

Group mappings, `mind` and `mind.dialects` cannot be `None`. Entity identity/description at any
record depth, `agent`, `runtime` and unknown schema fields are ineligible. `backend` is not copied
into a resolved secret component: it selects the default component and is not a credential field.

### 4.5 Baselines, omission and binding

The complete registry baseline consists of the marker, `agents: {}`, `paths` and `env_vars` in
§§2–4, and these defaults groups:

```yapyon
defaults:
  persona: {}
  harness: {}
  dialect: {}
  secret:
    backend: None
    root: "agents"
```

The following additional specification fallbacks apply when assembling a definition. They remain
deferred until final scope, rather than being evaluated into the literal registry. They are lower
than eligible store defaults and file settings:

| Definition field | Fallback when omitted |
|---|---|
| `agent.format` | The explicitly selected profile marker, under §2.3 |
| `agent.name` | The selected registered name; binding overrides authored names, under §3.2 |
| `agent.secret` | The current default selection, under §7.1 |
| `persona.mind.model_list` | `[]` |
| `persona.mind.model_active` | First model-list item, or `None` for an empty list |
| `persona.mind.model_subagent` | The final `model_active` value |
| `harness.path` | The selected registered agent directory with `/harness` appended |
| `harness.protocol` | Preferred-first compatible selection, under §6.4 |
| A selected secret mapping's `root` | Effective `runtime.defaults.secret.root` |
| A selected secret mapping's `entry` | The deferred root/name expression in §7.2 |

There are **no other implicit definition values**. In particular no persona, harness, enabled
dialect, endpoint, component identity, fetch command, native output or verification operation is
invented. Other optional fields remain absent unless supplied by an eligible default or source;
absence is not a hidden `None`. Descriptive fallbacks such as `desc: y"{name}"` are source conventions,
not identity defaults. `None` is valid only where the field's type permits it.

For each selected entity, the resolver MUST implement these observable rules:

1. Compose the explicit file contributions with their authored yapyon order/operators, retaining
   deferred values, dependencies and replacement intent. No file has a privileged base tier.
2. Determine applicable specification and store defaults using the fixed schema above, not the
   fields that happened to appear in source. Overlay schema-record defaults recursively; a supplied
   leaf/data/list value replaces its lower default whole. Per-protocol defaults are more specific
   than generic dialect defaults within the same store-default level.
3. Bind missing schema-record fields recursively while source is deferred. A supplied leaf/data/list
   value, including valid `None`, `[]` or `{}`, blocks its default; an empty schema-record mapping
   still permits defaults for its omitted fields. An explicit source replacement of a record is a
   reset boundary: do not resurrect lower defaults below it. A missing required field after such a
   reset is a validation error, not permission to undo the reset.
4. Bind registry identity and invocation-owned runtime inputs, then resolve expressions in final
   scope and validate the selected definition. Never merge resolved defaults into an already
   resolved definition or evaluate a selected backend before it has the final agent name/root.

This is a semantic contract, not a mandated sequence of tree API calls. An implementation must
preserve ordinary non-associative source history where moving contributions would change results.
Valid deferred constructs in the required baseline MUST receive these semantics. Inability to bind
one faithfully is an implementation defect and prevents a claim of core conformance. An incomplete
implementation MUST report that deficiency before saving/returning success; it MUST NOT ignore
defaults, freeze values or present the refusal as a restriction of the format. Fail-closed behavior
prevents corrupt output; it does not substitute for implementing required behavior.

For example, store `model_list: ["default-model"]` with file `model_list: []` resolves to the authored
empty list, not a concatenation. Store `context_size: 200000` supplies an omitted field, but file
`context_size: None` remains `None`. File `mind: {}` allows missing mind fields to receive defaults;
file `mind:= {}` resets the record and can therefore fail its required endpoint/dialects checks.
Native `config_store: {}` remains an empty native mapping even if the store has native defaults.

## 5. Source components and composition

### 5.1 Named component lookup

Every named slot is resolved from the configured **shared include root**, regardless of where
that slot occurs: an entry document, another shared file, a nested component or an override.
Qualified labels are Java-style path names: replace each dot with a directory separator and append
`.tmpl` to the final segment. The entire label identifies the file; it is not the former id.kind
spelling or an internal-field traversal within the loaded file.

| Slot label | Path relative to the shared include root |
|---|---|
| `agent.shared_base` | `agent/shared_base.tmpl` |
| `persona.local` | `persona/local.tmpl` |
| `harness.example_client` | `harness/example_client.tmpl` |
| `dialect.chat` | `dialect/chat.tmpl` |
| `secret.example_secret` | `secret/example_secret.tmpl` |

The same rule extends to deeper qualified names; namespace segments do not select a different
include root. Lookup is never relative to the including file's directory and does not search the
entries directory or invocation directory first. A nested `secret.example_secret` reference inside
`shared/secret/alternate_secret.tmpl` still selects the one global shared-root-relative file.

Each component document retains its single literal top-level branch, such as `persona` or `secret`.
Computed top-level branch keys are invalid: the adapter must not silently discard an unevaluated key
expression while selecting its value. A `runtime` branch is never persisted in component source.
The resolver supplies that branch's value as the slot filler and applies the authored slot overrides
under yapyon semantics. It does not interpret the filename label a second time as an internal
branch path. A component's descriptive `name` does not redirect include lookup. A dependency must
be available through this explicit source contract or already faithfully composed into saved
source, not guessed from a changing private application catalog.

Files MAY explicitly reference other files through ordinary yapyon slots/composition. Reuse does
not create a special file type or tier: a file informally called a base is simply another file in
the collapse. Writers MAY preserve those dependencies or faithfully compose their contributions;
neither persistence strategy is required. An installed `agent.cfg` MAY retain
`agent<agent.shared_base>` inheritance. A reader resolves that referenced source through the same
shared-root rule as every other named slot. PG's internal-source/collapsed-storage strategy does
not restrict the format. No store must materialize an entire reusable library merely to be valid.
The shared directory contains source dependencies, not registrations or a second agent-discovery
mechanism, and contributes no implicit defaults tier.

Resolution MUST NOT fall back to an application's changing bundled catalog, download a preset,
create a missing component or overwrite an existing one. A writer may provision components as
an explicit operation. Once stored, they are the dependencies readers use, not a cache to refresh
whenever unrelated agents are created. A missing dependency is an error.

Qualified labels consist of valid name segments; empty segments, literal path separators and
traversal spellings are invalid. Do not impose a two-segment limit or infer a fixed file category
from a former suffix convention. Missing include files, invalid document branches, cycles and
unfilled abstract slots are errors. A reader MUST track the dependency graph and impose finite
depth/size limits; it MUST NOT loop indefinitely or return a truncated definition. Repeated uses
of a source file are allowed; a repeated dependency is not itself a cycle. Existing symlink policy
still applies to include files; rooting the label is not a new filesystem-wide symlink prohibition.

### 5.2 Interpreting source

Fill named slots using their selected component source, then apply their authored overrides in
yapyon order. Fill invocation-owned abstract slots before final expression resolution. Do not
resolve each component to plain values independently: references bind in the assembled scope and
must see final agent, persona, harness and runtime values.

Ordinary `:` combines compatible mappings and collections according to yapyon. `:=` replaces
the complete field. Higher `None` replaces a container; it is not omission. Do not replace all
collection composition with dictionary update or list concatenation. A `(reference)` copies a
whole value with its type; `y"{reference}"` produces text and is not a typed copy. Unknown or
unresolved references are errors, not strings to pass through as successful output.

A resolver MUST distinguish source-schema fields from free-form native data. It MUST NOT prune
`None`, false-like values, empty collections or unknown native keys globally. An author may
explicitly transform a copy, for example `config_store.__not_none__()`, before serializing it.
That transformation does not change the underlying source/configuration tree.

### 5.3 Persisting source

Writers MUST preserve deferred references, remaining component dependencies, explicit replacement
intent and meaningful composition order. They MAY normalize comments and whitespace; byte-for-byte
source preservation is not required. A source serialization that cannot faithfully retain semantics
MUST fail before replacing existing output. Resolving a template and dumping the result is not a
faithful source save.

A saved agent document is not necessarily a portable dependency bundle. A source export MUST
identify itself as partial when it still depends on store components or runtime inputs. A flattened
resolved export MUST identify the inputs/context it captured; it MUST NOT claim that future store
edits will be reflected in that snapshot.

## 6. Agent definition and runtime inputs

### 6.1 Source root and runtime ownership

A persisted agent document has only the top branch `agent`, as a direct mapping or a named
agent slot. Either may retain live component dependencies. This direct-mapping example is
one permitted form, not a requirement to collapse inherited agent source:

```yapyon
agent:
  format: "agents-yapyon-v0.6.5"
  name: "scout"
  desc: y"{name}"
  secret: None
  persona<persona.local>: {}
  harness<harness.example_client>: {}
```

`runtime` is supplied by the resolver, never persisted in an agent or component document:

| Runtime field | Meaning |
|---|---|
| `runtime.agent_path` | Absolute registered agent-directory path for this resolution |
| `runtime.defaults` | Effective store defaults from §4 |
| `runtime.secret_backend` | Deferred selected default backend source, or `{}` if none |

An authored `runtime` branch or `agent.path` is invalid. There is no `runtime.auth_token` in this
profile. An information query/resolution does not require credentials. Use the registry location
for `runtime.agent_path`; do not infer it from `agent.name`. Its resolved path spelling may follow
filesystem canonicalization, but MUST refer to the selected registered directory.

### 6.2 Resolved agent fields

| Field | Type / requirement |
|---|---|
| `format` | Required string; profile marker |
| `name` | Required registered name |
| `desc` | Optional string; conventional base expression is the name |
| `persona` | Required persona mapping, §6.3 |
| `harness` | Required harness mapping, §6.4 |
| `secret` | `None` or selected backend mapping, §7 |

A resolver MUST validate types after composition, not merely accept syntactically valid source.
A missing required field, unresolved slot or invalid value is not a complete definition. In §6,
only fields labeled required (and the required mappings/name/path/protocol explicitly stated in
prose) must be present; other fields may be absent, with their specified type when present.
Specification defaults, eligible user defaults from §4 and explicitly inherited base source may
supply omitted values without duplicating them in each agent. Their absence from the agent's
literal source is not itself an error. A resolver MUST NOT fill unrelated fields from an arbitrary
private application template. The three-level cascade and ordinary file composition in §4 apply;
neither keyless selection nor a selected backend authorizes implicit clearing/deletion of authored
authentication fields.

### 6.3 Persona and dialects

A persona requires a nonempty `name` string and a `mind` mapping; `desc` is an optional string:

| Mind field | Type / meaning |
|---|---|
| `endpoint` | Required nonempty `http://` or `https://` URL; no credential retrieval implied |
| `context_size` | Positive integer or `None`; boolean is not an integer here |
| `model_list` | Ordered list of model-ID strings; default `[]` |
| `model_active` | Model-ID string or `None`; omitted-field fallback is first model, else `None` |
| `model_subagent` | Model-ID string or `None`; omitted-field fallback is final `model_active` |
| `dialects` | Required mapping from protocol name to enabled dialect mapping or `None` |

The endpoint is an absolute HTTP(S) URL with a nonempty host, not just a matching scheme prefix.
Validation does not resolve DNS, contact that host or normalize authored URL paths. Protocol-map
keys are exact nonempty strings; they need not be include-label identifiers. Dialect URI fields
are authored strings: consumers MUST NOT invent slash insertion, endpoint joining or mount rewrites.

A model ID is opaque text, not an agent identifier. Do not invent a remotely available model,
perform discovery or require a provider request to validate the stored definition. An explicitly
selected model need not be an element of `model_list`; a particular harness may impose stricter
requirements. Optional `None` model fields are meaningful.

An enabled dialect requires nonempty `name` and `api_uri` strings. Optional operation fields
`msg_uri`, `model_uri` and `emb_uri` are nonempty strings or `None` when unsupported.
`verify` is absent, `None` or a mapping with optional `check_uri` and `key_header` strings,
`headers` (list of strings) and `body` (string). A verifier must explicitly define any defaults
it needs for absent verification fields. These describe an optional verification operation; reading
them does not authorize a network request. A disabled dialect is retained as `None`, not globally
removed from raw data. Additional component data follows §10.

### 6.4 Harness and native output

A harness has these profile fields:

| Field | Type / meaning |
|---|---|
| `name` | Required nonempty string identifying the harness |
| `desc` | Optional descriptive string |
| `path` | Required nonempty path string; omitted-field fallback is `y"{runtime.agent_path}/harness"` |
| `auth_var` | Environment-variable name receiving a credential, or empty string if unused |
| `path_var` | Environment-variable name receiving the native directory, or empty string |
| `wrapper_env` | Mapping of environment-variable names to string values |
| `config_file` | Relative native filename, or `None`/empty string for no main file |
| `config_store` | Free-form native configuration mapping |
| `content` | String containing the explicitly serialized native output |
| `supported_dialects` | Required nonempty ordered list of protocol names, preferred first |
| `protocol` | Required selected supported, enabled dialect name |

**Authentication-variable references:** selecting `agent.secret: None` disables credential-backend
fetch/store operations; it does not establish that an authentication environment variable is
unavailable. This selection MUST NOT by itself clear an authored authentication-variable reference
(such as `harness.auth_var`) or a native field such as `env_key`. A value may be supplied by explicit
wrapper configuration, the inherited environment or another deliberately configured mechanism.
Harness-authored conditions/output transformations may express the required native configuration;
there is no generic standard clearing step. A native client's distinction between an omitted
field, an empty field and an empty environment value belongs to that client's configuration contract.

**Native authentication entries:** selecting a credential backend MUST NOT by itself delete an
authored native environment entry merely because its key matches `auth_var`. There is no generic
placeholder-removal exception in the standard. A harness need not declare the authentication key
in `config_store.env` at all: `auth_var` can still identify the variable supplied by its wrapper or
other credential consumer. If an optional native entry is authored as `None`, an explicit output-copy
transformation such as `__not_none__()` may omit it while preserving raw data. Native-client or
consumer-specific requirements must be handled by that configuration/consumer, not by silently
rewriting store data. A placeholder need not be introduced merely to create a value that another
resolution step then removes.

In this profile, resolved `harness.path` MUST identify `<runtime.agent_path>/harness`. Agent
relocation changes the registry path, not a hidden harness directory override. A nonempty native filename
MUST be relative and contain no `..` segment. These are lexical location constraints; explicit
filesystem links remain subject to §3.4, not an implied new physical-containment or no-link policy.
Filesystem path strings MUST NOT contain NUL. `auth_var` and `path_var`, when nonempty, and all
`wrapper_env` keys MUST use the environment-name syntax in §4.1; wrapper values are strings. Native configuration
inside `config_store` is not an extension of persona fields; its meaning belongs to the harness.

Unless explicitly overridden to another compatible supported protocol, `protocol` is the first
name in `supported_dialects` whose persona dialect is enabled. An empty intersection is a
compatibility error. Merely writing a configuration is not proof the harness or remote endpoint
accepts it. The store profile does not prescribe installers' placeholder-key behavior.

## 7. Credential selection and locators

### 7.1 Source forms

| Source form inside `agent` | Binding |
|---|---|
| `secret<>: {}` | Current store default backend |
| `secret<>: {entry: "shared/team"}` | Current default, with complete-entry override |
| `secret<secret.example_secret>: {}` | Explicit shared-root include, independent of default backend selection |
| `secret: {...}` | Complete inline backend, not a partial default override |
| `secret: None` | Explicitly keyless |

Fill the selected backend before resolving its entry and command expressions. Never eagerly
resolve a default backend outside the agent's final scope. An explicit component still inherits
any store-default values its own source references; “independent” refers to backend selection,
not an automatic freeze of every inherited field.

At creation, if no backend is selected/configured, a writer MUST persist explicit `secret: None`.
If a default backend is configured and no per-agent override is requested, it SHOULD preserve a
default slot rather than copy today's resolved backend. For an existing saved source that omits
`secret`, a resolver uses the current default binding; it MUST NOT rewrite the source just to
supply that runtime value. A default slot without a configured backend resolves to keyless only
when it has no meaningful overrides; overrides require a backend and otherwise fail.

Default-slot agents follow later default-backend changes. Explicitly keyless agents remain
keyless when defaults change. Explicit named and inline backends do not silently switch to a
new default backend. These are distinct states, not interchangeable spellings of omission.

### 7.2 Backend fields

| Field | Type / requirement |
|---|---|
| `name` | Required nonempty backend-ID string |
| `root` | Manager-relative root string or `None`; omitted-field fallback is effective store root default |
| `entry` | Required complete nonempty manager-relative entry string |
| `fetch` | Required nonempty command string |
| `store` | Optional command string or `None`; imports require it |
| `probe` | Optional executable-name/path string or `None` |
| `check` | Optional readiness command string or `None` |

A complete inline backend requires `name`, `entry` and `fetch` after the defaults/source binding
in §4.5. A plain inline mapping does not select or copy the configured default backend's fields;
it can receive eligible field defaults, just as an explicitly named component can. The standard
root/entry fallbacks remain available. An authored complete entry/command need not reference root. Manager entries are not host filesystem paths.
For a string root or entry, prohibit leading/trailing `/`, empty segments, `.`/`..` segments,
a leading `-`, NUL, carriage return and newline. An empty root is invalid; use `None` instead.

The conventional base entry expression is:

```yapyon
entry: y"{root}/{agent.name}" if root is not None else agent.name
```

With root `"agents"` and name `"scout"`, the complete entry is `"agents/scout"`. With root
`None`, it is `"scout"`, and the agent is still keyed. An explicit `entry` is already complete;
consumers MUST NOT prepend the root again. Two agents may intentionally select the same entry.
A rename changes a name-derived entry, not a fixed explicit entry, and does not move the manager's
record. A writer SHOULD warn about that distinction before a rename affecting credential lookup.

### 7.3 Executing commands is a separate role

Commands are inert data during registry queries, source reads and definition resolution. Explicit
credential consumers construct argument vectors, never an implicit shell command. For each nonempty
`fetch`, `store` or `check` command:

1. If the command ends with the complete `entry` string and the preceding prefix ends with a space
   or tab, parse only that prefix using POSIX quoting/backslash rules, then append the exact entry
   as **one argument**. Spaces, quotes and metacharacters inside that final entry remain data.
2. Otherwise, parse the whole command using those POSIX argument-splitting rules. Authors must quote
   embedded/nonfinal entry arguments correctly; no general substitution or substring repair applies.

The argument vector must have a nonempty executable and contain no NUL. Invalid quoting is an
error. Optional command/probe fields may be absent, `None` or empty strings to indicate that the
operation is not provided. A consumer requiring that operation must report it unavailable; it
must not attempt to execute an empty or whitespace-only command. `probe`, when supplied, is a single executable name/path, not a shell command. Consumers
MUST NOT perform shell expansion, pipelines, redirections or command substitution, or reconstruct
a shell command to make an invalid vector work. This profile deliberately retains string command
fields; a future structured-argv representation would require an explicit contract.

`fetch` emits the credential to stdout; `store` receives it on stdin. Secret values MUST NOT be
appended to an argument vector, persisted in registry/source, interpolated into native output,
or included in diagnostics. Execution requires user/caller authorization and appropriate trust
in the source; format validity alone is not execution permission. A configured command may itself
be an interpreter and is not made safe merely by avoiding a shell. The manager-specific credential
encoding, newline/whitespace normalization, process environment, timeouts and output limits are
part of the credential consumer's interface, not hidden source-resolution behavior. A consumer
must document them and refuse a representation it cannot carry faithfully. This profile does not
standardize binary credentials or a manager's command-line protocol beyond the argv/stdin/stdout
boundaries above. Nonzero exit, malformed output and an unusable empty credential are failures,
not successful keyless selections.

Manager absence, failed lookup, an unknown backend state and explicit keyless selection are
different outcomes. A consumer MUST NOT convert errors into an invented key or silently run an
agent as keyless. Read-only resolution MUST NOT initialize a manager, import a token, prompt for
one or probe a provider. Removing an agent MUST NOT delete manager credentials implicitly.

## 8. Reads, writes, freshness and launch

Registry listing does not resolve every agent or fetch keys. A bad unrelated agent source need
not prevent listing a valid registry. Resolving a named agent validates that agent's dependencies;
a dangling registration MUST be reported rather than silently repaired or removed. Metadata
retrieval, explicit credential retrieval and launch MUST be distinguishable operations.

Each resolution uses current source and an explicit runtime/environment snapshot. A resolver MAY
cache only when it can establish that all relevant source, registry/default and runtime inputs
are unchanged. Native settings and installed wrappers are snapshots: editing a shared component
does not itself update them. A launcher MUST disclose whether it uses a snapshot or resolves
source at launch; this draft does not require launch-time resolution or automatic installation.

This layout has no global generation manifest or standardized locking protocol. A reader SHOULD
avoid mixing known-changed inputs within one operation, and MUST report detected mid-read changes
rather than describe a known mixture as a coherent snapshot. Readers/writers MUST NOT promise a
cross-file transaction or crash consistency that their implementation does not provide.

A writer SHOULD prepare and validate candidate source before replacing existing files, use atomic
replacement where supported, and detect intervening edits before committing prepared state. Registry
updates MUST preserve unrelated registrations and authored settings. A late IO
failure MUST report what was saved; it MUST NOT trigger implicit deletion of credentials or unrelated
data. Consumers may require stronger external locking, ownership or trust policies without changing
what the stored fields mean.

## 9. Validation and diagnostics

Validation is staged: decode/parse; validate registry schema/version; load selected source and
dependencies; fill slots and bind runtime inputs; resolve; validate the typed definition. A tool
MUST distinguish “source parsed”, “source saved faithfully” and “definition resolved and validated”.
None proves provider availability, credential validity, native harness acceptance or successful launch.

At minimum report these failure classes without requiring these exact error strings:

- IO/path/permission failure, including dangling links and missing selected dependencies.
- Malformed UTF-8 or yapyon, non-record registry, or invalid fixed-schema field/type.
- Missing/unsupported format, or syntax/functions outside the profile.
- An implementation deficiency preventing required core processing; this is not invalid source or
  a conformance exemption.
- Agent not registered, invalid identifier or resolved identity/binding mismatch.
- Component cycle, missing branch, abstract slot or unresolved reference/environment access.
- Invalid persona/harness compatibility, backend locator or command representation.
- Caller trust-policy refusal, resource-limit refusal or detected stale candidate/input.
- Credential execution failure, only for an explicit credential operation.

Failures MUST NOT emit a partly resolved definition or credential on a success channel. Diagnostics
SHOULD identify the file, field and relevant source location without exposing credential values or
credential-bearing process output. Tools may return partial metadata only when explicitly labeled
partial, not as a substitute for a successful requested definition. Limits MUST cause a clear error,
not truncation. No particular exception class, CLI exit number or Python API is part of the format.

## 10. Extensions and compatibility

The registry, registration record and direct `agent` mapping are closed to unknown profile fields.
`defaults` has the recursive specification-field scope and entity-identity exclusions in §4; it is
not restricted to any implementation's subset. Validate applicable boundaries after composition
as well as in literal source, so a computed key cannot bypass the schema. A misspelled field is not
automatically an extension.

Persona, mind, harness, dialect and secret mappings may contain additional author-defined data.
A reader MUST preserve and return that data when it returns the whole definition, but MUST NOT
invent standard meaning for it. The defined fields still have their types and requirements;
additional data does not excuse a missing or misspelled required field. All expressions, including
those in additional data, must resolve or fail normally. Free-form `config_store` and arbitrary
dialect-map names are intentionally not closed-schema boundaries.

A dedicated `custom` (or similarly named) entity-metadata namespace is deferred to a future
version and is not added to this draft. Existing open-component data is not thereby standardized
or made eligible for user-wide defaults. This draft does not invent a new registry extension
manifest, plugin import contract or mandatory metadata namespace. Applications SHOULD namespace
additional component data to avoid future name collisions. Extra data MUST NOT override runtime ownership or environment policy, and its presence
alone never authorizes execution. Required new semantics or incompatible source interpretation
need an explicit future profile/contract rather than silently changing this one.

The former persona-matrix store, YAML+ drafts, `PERSONA_STORE_DIR`, token-path pointer files and
legacy designation selectors are not compatibility schemas for this profile. Existing data MUST
NOT be removed merely because a reader does not support it. Any migration is a separate, explicit
operation with independently validated source and credential behavior.

## 11. Examples and implementation boundary

[CONFORMANCE.md](CONFORMANCE.md) organizes the role-specific acceptance cases. It is an informative
checklist, not a second normative schema or a claim that a particular implementation passes them.

`examples/` contains a synthetic, self-contained store and an offline validator. Its paths are
illustrative, its backend commands inert, and its endpoints are not live acceptance targets.
The protected `sample/` files remain historical inputs: the defaults use `v0.6` and the registry
is intentionally empty. They have not been rewritten into an allegedly approved standard.

Released PG **0.0.7** is evidence for many mechanics in this draft, but not a conformance certificate.
That release uses `v0.1`, secret-only store defaults, collapsed agent-base persistence, extra shell
keyword reservations and authentication normalization that differs from this profile. Any later
implementation must be checked against this specification rather than inferred from that release
or a silent marker edit. Implementation status belongs to the implementation's own records, not
the meaning of this marker. This document does not itself execute or authorize a real-store/consumer
migration or publication.
