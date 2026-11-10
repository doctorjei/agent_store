# Candidate agent_store examples

**DRAFT 0.6.5.** These fixtures illustrate [the candidate specification](../SPEC.md); they are not an
installed store, live provider configuration or credential-backend integration. The
[conformance guide](../CONFORMANCE.md) lists the broader role-specific acceptance cases.

The conventional directories are `shared/` for include source and `entries/` for individual
agent entrypoints. Their store-config defaults are `paths.shared: "shared"` and
`paths.entries: "entries"`; neither needs to be written when its default is intended. Registry paths
are explicit absolute locations under a fictional `/example/agents` root and must agree with the
intended entry locations; changing the entries default does not rewrite existing registrations.

Every qualified named slot is rooted at the same configured shared include directory, including
slots inside shared files. `persona<persona.local>` selects `shared/persona/local.tmpl`, while
`harness<harness.example_client>` selects `shared/harness/example_client.tmpl`. A file in
`shared/secret/` referring to `secret.example_secret` does not use its own directory as a new root.
Optional `shared/agent/shared_base.tmpl` demonstrates reusable ordinary source; preserving or
faithfully composing its dependencies is permitted. Its retained form passes through the abstract
secret slot:

```yapyon
agent<agent.shared_base>:
  secret<>: {}
```

All three agents share the local persona, example harness and chat dialect. The persona reads
`AGENT_STORE_EXAMPLE_ENDPOINT` from the resolver's explicit environment snapshot. Validation
supplies `http://127.0.0.1:8000`; no request is made. `example-model` is an opaque synthetic ID.

| Agent | Selection | Resolved credential locator |
|---|---|---|
| `scout` | Explicit `secret: None` | Keyless, even if the default backend changes |
| `unprefixed` | Explicit `secret.example_secret`, `root: None` | Backend `example_secret`, entry `unprefixed` |
| `shared` | Default slot, complete entry override | Current default backend, entry `shared/team` |

`shared/secret/alternate_secret.tmpl` is an additional component used to demonstrate changed defaults.
The default backend selector `example_secret` identifies `secret.example_secret`. The example's
`env_vars.from_host` and `env_vars.additions` hold the allowed host-environment names. The
`example-manager` and `alternate-manager` command strings are deliberately inert examples, not
programs to install or run. No document contains a credential. Root `None` removes a prefix;
it does not disable credential selection.

## Offline validation

The checker uses the configured shared include root, namespace paths, nested environment settings
and explicit registered entry locations. It checks that changing the entries convention does not
redirect an existing registration, and that missing records are not hidden by name-based fallback.

Run the checker with:

```sh
nice -n 19 ~/.venvs/pg/bin/python -I ~/workspace/agent_store/validate_examples.py
```

Use an interpreter with yapyon 0.6.5-compatible semantics; the particular venv path is local
convenience, not part of the format. `validate_examples.py --help` describes its scope/options.
It checks concrete resolved values, source-save/reload under changed inputs, default/keyless/
explicit backend distinctions, authentication fields preserved without implicit normalization,
false-like native values, recursive defaults field eligibility/identity exclusions, retained source,
configured include roots, nested/deeper namespaces and selected error cases. Precedence is specification defaults, then store-config defaults, then ordinary
file settings, with no special tier for a reused file. The bounded fixture resolver does not implement
generic default application and explicitly refuses it rather than silently ignoring it. Authentication
checks follow the settled no-mutation rules, unlike released PG 0.0.7; development implementations
need their own acceptance checks. The checker
never executes manager commands, fetches credentials, installs files or launches a harness. It does not import `persona_grata`.

The checker is a bounded executable example, **not a complete conformance suite or production
store reader**. It does not validate every optional schema field, filesystem mutation/link race,
platform command convention or source construct allowed by the specification. Successful checks
do not establish provider availability, native-harness acceptance or an adopted `v0.6.5` format.

Released PG 0.0.7 supports `agents-yapyon-v0.1`, not these candidate `v0.6.5` markers. Pointing
that release at this directory is not supported. A later implementation needs its own acceptance
checks; this fixture's fictional registrations do not name real installed agent directories. Semantic probes of earlier drafts do not establish compatibility
with these revised paths, namespaces, schema or no-mutation rules. The separate protected `../sample/` inputs
remain unchanged, including their intentionally empty registry.
