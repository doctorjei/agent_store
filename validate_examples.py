#!/usr/bin/env python3
"""Check the candidate agent_store examples without credentials or installation.

Run with a Python environment containing yapyon 0.6.5-compatible semantics:
  nice -n 19 ~/.venvs/pg/bin/python -I ~/workspace/agent_store/validate_examples.py

--examples selects another copy of this synthetic fixture. Registry paths remain
logical /example/agents paths; no real store is discovered. This is an executable
example/semantic regression check, not a production reader or full conformance
suite. It never executes backend commands, launches a harness, accesses a provider,
imports PG, reads the process environment into documents, or writes store files.
The defaults cascade is specified, but generic application is not implemented by
this bounded fixture resolver: it refuses unsupported bindings rather than ignore them.
Named slots use qualified paths under the configured shared include root, never
the including file's directory. Auth fields are preserved without implicit PG
normalization. Retained and composed ordinary source forms are tested.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import sys
import tempfile
import unittest

import yapyon


FORMAT = "agents-yapyon-v0.6.5"
LOGICAL_ROOT = PurePosixPath("/example/agents")
RESERVED_ENV = {"HOME", "XDG_CONFIG_HOME", "AGENT_STORE_DIR"}
STANDARD_ENV = [
    "COLUMNS", "DATEMSK", "HOME", "LANG", "LANGUAGE", "LC_ALL", "LC_COLLATE",
    "LC_CTYPE", "LC_MESSAGES", "LC_MONETARY", "LC_NUMERIC", "LC_TIME", "LINES",
    "LOGNAME", "MSGVERB", "NLSPATH", "PATH", "PWD", "SHELL", "TERM", "TEXTDOMAIN",
    "TEXTDOMAINDIR", "TMPDIR", "TZ", "XDG_CACHE_HOME", "XDG_CONFIG_DIRS",
    "XDG_CONFIG_HOME", "XDG_DATA_DIRS", "XDG_DATA_HOME", "XDG_RUNTIME_DIR",
    "XDG_STATE_HOME",
]
BASELINE = {
    "format": FORMAT,
    "agents": {},
    "defaults": {"persona": {}, "harness": {}, "dialect": {},
                 "secret": {"backend": None, "root": "agents"}},
    "paths": {"shared": "shared", "entries": "entries"},
    "env_vars": {"from_host": STANDARD_ENV, "additions": []},
}
DIALECT_DEFAULTS = {
    "api_uri": None, "msg_uri": None, "model_uri": None, "emb_uri": None,
    "verify": {"check_uri": None, "key_header": None, "headers": None, "body": None},
}
DEFAULT_FIELDS = {
    "persona": {"mind": {
        "endpoint": None, "context_size": None, "model_list": None,
        "model_active": None, "model_subagent": None, "dialects": "dialects",
    }},
    "harness": {
        "path": None, "auth_var": None, "path_var": None, "wrapper_env": "data",
        "config_file": None, "config_store": "data", "content": None,
        "supported_dialects": None, "protocol": None,
    },
    "dialect": DIALECT_DEFAULTS,
    "secret": {
        "backend": None, "root": None, "entry": None, "fetch": None,
        "store": None, "probe": None, "check": None,
    },
}
AGENT_FIELDS = {"format", "name", "desc", "persona", "harness", "secret"}
FIXTURE_ENV = {
    "HOME": "/example/home",
    "AGENT_STORE_EXAMPLE_ENDPOINT": "http://127.0.0.1:8000",
}
EXAMPLES = Path(__file__).resolve().parent / "examples"


def literal(value):
    return yapyon.parse(yapyon.dumps(value))


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", value):
        raise ValueError("invalid identifier")
    if value == "default":
        raise ValueError("reserved identifier")


def entry(value):
    if (not isinstance(value, str) or not value or value.startswith(("/", "-"))
            or any(char in value for char in "\0\r\n")
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("invalid manager-relative entry")


def command_argv(command, complete_entry):
    if not isinstance(command, str) or not command.strip() or "\0" in command:
        raise ValueError("invalid backend command")
    prefix = command[:-len(complete_entry)]
    if command.endswith(complete_entry) and prefix.endswith((" ", "\t")):
        argv = shlex.split(prefix, posix=True) + [complete_entry]
    else:
        argv = shlex.split(command, posix=True)
    if not argv or not argv[0] or any("\0" in argument for argument in argv):
        raise ValueError("invalid backend argument vector")
    return argv


def overlay(base, higher):
    result = deepcopy(base)
    for key, value in higher.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = overlay(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def validate_defaults(values, fields=DEFAULT_FIELDS):
    if not isinstance(values, dict):
        raise ValueError("defaults groups must be mappings")
    for key, value in values.items():
        if key in {"name", "desc"}:
            raise ValueError("entity identity is not defaultable")
        if key not in fields:
            raise ValueError("unknown specification default field")
        schema = fields[key]
        if isinstance(schema, dict):
            if value is None and key == "verify":
                continue
            validate_defaults(value, schema)
        elif schema == "data":
            if not isinstance(value, dict):
                raise ValueError("native/environment defaults must be mappings")
        elif schema == "dialects":
            if not isinstance(value, dict):
                raise ValueError("dialect defaults must be a mapping")
            for protocol, dialect in value.items():
                if not isinstance(protocol, str) or not protocol:
                    raise ValueError("invalid protocol name")
                if dialect is not None:
                    validate_defaults(dialect, DIALECT_DEFAULTS)


def registry(text):
    meaningful = any(line.strip() and not line.lstrip().startswith("#")
                     for line in text.splitlines())
    raw = yapyon.loads_record(text) if meaningful else {}
    if not isinstance(raw, dict) or set(raw) - set(BASELINE):
        raise ValueError("invalid registry fields")
    result = overlay(BASELINE, raw)
    if result["format"] != FORMAT:
        raise ValueError("unsupported store format")
    defaults = result["defaults"]
    validate_defaults(defaults)
    secret = defaults["secret"]
    if secret["backend"] is not None:
        identifier(secret["backend"])
    if secret["root"] is not None:
        entry(secret["root"])
    paths_config = result["paths"]
    if not isinstance(paths_config, dict) or set(paths_config) != {"shared", "entries"}:
        raise ValueError("invalid path settings")
    for path in paths_config.values():
        if not isinstance(path, str) or not path or "\0" in path:
            raise ValueError("path settings must be nonempty strings")
    environment = result["env_vars"]
    if not isinstance(environment, dict) or set(environment) != {"from_host", "additions"}:
        raise ValueError("invalid environment settings")
    for names in environment.values():
        if not isinstance(names, list) or any(
            not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            for name in names
        ):
            raise ValueError("invalid environment names")
    if not isinstance(result["agents"], dict):
        raise ValueError("invalid registrations")
    paths = []
    for name, record in result["agents"].items():
        identifier(name)
        if not isinstance(record, dict) or set(record) != {"path"}:
            raise ValueError("invalid agent record")
        path = record["path"]
        if not isinstance(path, str) or not PurePosixPath(path).is_absolute():
            raise ValueError("agent path must be absolute")
        path = PurePosixPath(path)
        if ".." in path.parts:
            raise ValueError("agent path contains parent traversal")
        if any(path == prior or path in prior.parents or prior in path.parents for prior in paths):
            raise ValueError("overlapping registrations")
        paths.append(path)
    return result


class FixtureResolver:
    """A bounded assembler for the synthetic fixture, without PG/catalog fallback."""

    def __init__(self, root, components=None):
        self.root = Path(root).resolve()
        self.components = components or {}

    def shared_root(self, settings=None):
        settings = BASELINE if settings is None else settings
        path = Path(settings["paths"]["shared"])
        return path if path.is_absolute() else self.root / path

    def component(self, label, settings=None, stack=()):
        if not label:
            raise ValueError("named component label cannot be empty")
        for segment in label:
            identifier(segment)
        if label in stack:
            raise ValueError("component cycle")
        if len(stack) >= 64:
            raise ValueError("component depth limit")
        path = self.shared_root(settings).joinpath(*label).with_suffix(".tmpl")
        text = self.components[label] if label in self.components else path.read_text(encoding="utf-8")
        tree = yapyon.parse(text, source=str(path))
        if tree.root.kind != "mapping" or len(tree.keys()) != 1 or "runtime" in tree:
            raise ValueError("component must have one non-runtime branch")
        self.fill_named(tree, settings, stack + (label,))
        return tree

    def fill_named(self, tree, settings=None, stack=()):
        for _ in range(256):
            selected = next((slot for slot in tree.slots() if not slot.abstract), None)
            if selected is None:
                return
            component = self.component(selected.label, settings, stack)
            selected.fill(component[next(iter(component.keys()))])
        raise ValueError("component fill limit")

    def source(self, name, settings):
        logical = PurePosixPath(settings["agents"][name]["path"])
        try:
            relative = logical.relative_to(LOGICAL_ROOT)
        except ValueError:
            raise ValueError("fixture paths must be beneath /example/agents") from None
        return yapyon.parse_file(self.root / str(relative) / "agent.cfg")

    def resolve(self, name, settings, source=None, env=None):
        defaults = settings["defaults"]
        if (any(defaults.get(group) for group in ("persona", "harness", "dialect"))
                or set(defaults["secret"]) - {"backend", "root"}):
            raise ValueError("generic default application is not implemented by this fixture resolver")
        if name not in settings["agents"]:
            raise ValueError("agent not registered")
        path = settings["agents"][name]["path"]
        tree = yapyon.merge(source if source is not None else self.source(name, settings))
        if set(tree.keys()) != {"agent"}:
            raise ValueError("source must have only agent; runtime is invocation-owned")
        self.fill_named(tree, settings)
        agent = tree["agent"]
        if set(agent.keys()) - AGENT_FIELDS:
            raise ValueError("unknown agent fields")
        if "format" not in agent:
            agent.merge(literal({"format": FORMAT}))
        marker = agent["format"]
        if marker.kind != "scalar" or marker.value != FORMAT:
            raise ValueError("unsupported source agent format")
        agent.merge(literal({"name": name}))
        if "secret" not in agent:
            agent.merge(yapyon.parse("secret<>: {}"))
        backend_id = settings["defaults"]["secret"]["backend"]
        backend = self.component(("secret", backend_id), settings) if backend_id is not None else None
        selected = agent["secret"]
        if selected.kind == "slot" and selected.abstract:
            if backend is None:
                if len(selected.overrides.root):
                    raise ValueError("default secret overrides require a backend")
                selected.replace(literal(None).root)
            else:
                selected.fill(backend["secret"])
        runtime = literal({"runtime": {
            "agent_path": path, "defaults": settings["defaults"], "secret_backend": {},
        }})
        if backend is not None:
            runtime["runtime"]["secret_backend"].replace(backend["secret"])
        tree = yapyon.merge(runtime, tree)
        self.fill_named(tree, settings)
        if tree.slots():
            raise ValueError("unfilled abstract slot")
        allowed = (RESERVED_ENV | set(settings["env_vars"]["from_host"])
                   | set(settings["env_vars"]["additions"]))
        result = tree.resolve(env=FIXTURE_ENV if env is None else env, env_allow=allowed)
        self.validate(result["agent"], name, path)
        return result

    @staticmethod
    def validate(agent, name, path):
        if set(agent) - AGENT_FIELDS or agent.get("format") != FORMAT or agent.get("name") != name:
            raise ValueError("invalid resolved agent identity/schema")
        persona, harness = agent.get("persona"), agent.get("harness")
        if not isinstance(persona, dict) or not isinstance(harness, dict):
            raise ValueError("persona and harness must be mappings")
        mind = persona.get("mind", {})
        endpoint = mind.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
            raise ValueError("invalid endpoint")
        size = mind.get("context_size")
        if size is not None and (type(size) is not int or size <= 0):
            raise ValueError("invalid context size")
        supported = harness.get("supported_dialects")
        if (not isinstance(supported, list) or not supported
                or any(not isinstance(item, str) or not item for item in supported)):
            raise ValueError("invalid supported dialects")
        protocol = harness.get("protocol")
        if (protocol not in supported
                or not isinstance(mind.get("dialects", {}).get(protocol), dict)):
            raise ValueError("no compatible selected dialect")
        if harness.get("path") != f"{path}/harness":
            raise ValueError("invalid harness path")
        secret = agent.get("secret")
        if secret is not None:
            if not isinstance(secret, dict):
                raise ValueError("secret must be a mapping or None")
            for required in ("name", "entry", "fetch"):
                if not isinstance(secret.get(required), str) or not secret[required]:
                    raise ValueError("incomplete secret backend")
            entry(secret["entry"])
            if secret.get("root") is not None:
                entry(secret["root"])
            for optional in ("store", "probe", "check"):
                if secret.get(optional) is not None and not isinstance(secret[optional], str):
                    raise ValueError("invalid backend command field")
            for command in ("fetch", "store", "check"):
                if secret.get(command):
                    command_argv(secret[command], secret["entry"])


class ExampleChecks(unittest.TestCase):
    def setUp(self):
        self.raw = (EXAMPLES / "agent_store.cfg").read_text(encoding="utf-8")
        self.settings = registry(self.raw)
        self.reader = FixtureResolver(EXAMPLES)

    def resolve(self, name="shared", **kwargs):
        return self.reader.resolve(name, self.settings, **kwargs)

    def changed(self, text, name="shared"):
        source = self.reader.source(name, self.settings)
        return yapyon.merge(source, yapyon.parse(text))

    def test_registry_and_sparse_defaults(self):
        self.assertEqual(set(self.settings["agents"]), {"scout", "unprefixed", "shared"})
        self.assertEqual(self.settings["defaults"]["secret"], {"backend": "example_secret", "root": "agents"})
        self.assertEqual(self.settings["env_vars"]["from_host"], [])
        self.assertEqual(self.settings["paths"], {"shared": "shared", "entries": "entries"})
        self.assertEqual(registry('defaults: {secret: {root: None}}')["defaults"]["secret"],
                         {"backend": None, "root": None})

    def test_recursive_specification_defaults_are_accepted(self):
        values = {"persona": {"mind": {"context_size": 200000, "model_list": []}},
                  "harness": {"supported_dialects": ["chat"], "wrapper_env": {"LANG": "C"}},
                  "dialect": {"verify": {"headers": []}},
                  "secret": {"entry": "shared/team", "check": "example-manager ready"}}
        parsed = registry(yapyon.dumps({"defaults": values}))
        for group, fields in values.items():
            for field, value in fields.items():
                with self.subTest(group=group, field=field):
                    self.assertEqual(parsed["defaults"][group][field], value)
        nested = {"persona": {"mind": {"dialects": {"chat": {"verify": {"body": ""}}}}}}
        self.assertEqual(registry(yapyon.dumps({"defaults": nested}))["defaults"]["persona"], nested["persona"])

    def test_identity_and_non_specification_defaults_are_rejected(self):
        for group in ("persona", "harness", "dialect", "secret"):
            for identity in ("name", "desc"):
                with self.subTest(group=group, identity=identity), self.assertRaises(ValueError):
                    registry(yapyon.dumps({"defaults": {group: {identity: "one-entity"}}}))
        for values in ({"agent": {}}, {"persona": {"mind": {"typo": 1}}},
                       {"persona": {"mind": {"dialects": {"chat": {"name": "one-entity"}}}}}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                registry(yapyon.dumps({"defaults": values}))

    def test_native_data_names_are_not_entity_identity_fields(self):
        native = {"name": "native-setting", "desc": "native-setting-description"}
        parsed = registry(yapyon.dumps({"defaults": {"harness": {"config_store": native}}}))
        self.assertEqual(parsed["defaults"]["harness"]["config_store"], native)

    def test_three_level_cascade_has_no_special_reused_file_tier(self):
        spec_defaults = literal({"persona": {"mind": {"context_size": 100000, "model_active": "spec-model"}}})
        store_defaults = literal({"persona": {"mind": {"context_size": 200000}}})
        reused_file = literal({"persona": {"mind": {"context_size": 300000}}})
        selecting_file = literal({"persona": {"mind": {"model_active": "file-model"}}})
        file_settings = yapyon.merge(reused_file, selecting_file)
        result = yapyon.merge(spec_defaults, store_defaults, file_settings).resolve(env={}, env_allow=set())
        self.assertEqual(result["persona"]["mind"], {"context_size": 300000, "model_active": "file-model"})
        no_reused_value = yapyon.merge(spec_defaults, store_defaults, selecting_file).resolve(env={}, env_allow=set())
        self.assertEqual(no_reused_value["persona"]["mind"]["context_size"], 200000)
        explicit_none = yapyon.parse("persona:\n  mind:\n    context_size: None")
        result = yapyon.merge(spec_defaults, store_defaults, file_settings, explicit_none).resolve(env={}, env_allow=set())
        self.assertIsNone(result["persona"]["mind"]["context_size"])

    def test_generic_defaults_are_not_silently_ignored_by_fixture_resolver(self):
        self.settings["defaults"]["persona"] = {"mind": {"context_size": 200000}}
        with self.assertRaisesRegex(ValueError, "not implemented by this fixture resolver"):
            self.resolve()

    def test_optional_external_agent_base_and_collapsed_form_agree(self):
        source = yapyon.parse('agent<agent.shared_base>:\n  secret<>: {}')
        saved = source.to_source()
        reference = self.resolve()
        self.assertEqual(self.resolve(source=yapyon.parse(saved)), reference)
        collapsed = yapyon.merge(source)
        self.reader.fill_named(collapsed)
        self.assertEqual(self.resolve(source=yapyon.parse(collapsed.to_source())), reference)
        self.assertEqual(source.to_source(), saved)
        self.assertIn("agent.shared_base", saved)

    def test_shell_keywords_are_valid_storage_names(self):
        for name in ("if", "then", "else", "elif", "fi", "do", "done", "case", "esac",
                     "while", "until", "for", "in", "function", "select", "time", "coproc"):
            with self.subTest(name=name):
                identifier(name)
        with self.assertRaisesRegex(ValueError, "reserved"):
            identifier("default")

    def test_blank_and_invalid_registries(self):
        for text in ("", " \n", "# empty registry\n"):
            with self.subTest(text=text):
                self.assertEqual(registry(text), BASELINE)
        for text in ('[]', 'None', '""', 'format: y"unsupported"'):
            with self.subTest(text=text), self.assertRaises((ValueError, yapyon.AkanError)):
                registry(text)

    def test_all_source_files_parse_and_save_unresolved(self):
        paths = sorted(EXAMPLES.rglob("*.tmpl")) + sorted(EXAMPLES.rglob("agent.cfg"))
        self.assertEqual(len(paths), 9)
        for path in paths:
            with self.subTest(path=path.relative_to(EXAMPLES)):
                tree = yapyon.parse_file(path)
                saved = tree.to_source()
                self.assertEqual(yapyon.parse(saved).to_source(), saved)

    def test_all_agents_resolve_concrete_values(self):
        for name in self.settings["agents"]:
            with self.subTest(name=name):
                result = self.resolve(name)
                agent = result["agent"]
                self.assertEqual(agent["name"], name)
                self.assertEqual(agent["format"], FORMAT)
                self.assertEqual(agent["persona"]["mind"]["endpoint"], "http://127.0.0.1:8000")
                self.assertEqual(agent["persona"]["mind"]["model_subagent"], "example-model")
                self.assertEqual(agent["harness"]["protocol"], "chat")
                self.assertEqual(agent["harness"]["path"], f"/example/agents/entries/{name}/harness")

    def test_configured_shared_roots_are_store_relative_or_absolute(self):
        for absolute in (False, True):
            with self.subTest(absolute=absolute), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "fixture"
                shutil.copytree(EXAMPLES, root)
                (root / "shared").rename(root / "includes")
                settings = deepcopy(self.settings)
                settings["paths"]["shared"] = str(root / "includes") if absolute else "includes"
                agent = FixtureResolver(root).resolve("shared", settings)["agent"]
                self.assertEqual(agent["secret"]["entry"], "shared/team")
                self.assertEqual(agent["persona"]["mind"]["endpoint"], "http://127.0.0.1:8000")

    def test_nested_include_keeps_the_global_shared_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            shutil.copytree(EXAMPLES, root)
            original = (root / "shared/secret/example_secret.tmpl").read_text(encoding="utf-8")
            needle = "root: (runtime.defaults.secret.root)"
            self.assertEqual(original.count(needle), 1)
            decoy = root / "shared/secret/secret/example_secret.tmpl"
            decoy.parent.mkdir(parents=True)
            decoy.write_text(original.replace(needle, 'root: "wrong-relative-root"'), encoding="utf-8")
            settings = deepcopy(self.settings)
            settings["defaults"]["secret"]["backend"] = "alternate_secret"
            secret = FixtureResolver(root).resolve("shared", settings)["agent"]["secret"]
            self.assertEqual(secret["name"], "alternate_secret")
            self.assertEqual(secret["root"], "agents")

    def test_deeper_qualified_names_are_paths_not_internal_branch_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            shutil.copytree(EXAMPLES, root)
            target = root / "shared/acme/providers/local.tmpl"
            target.parent.mkdir(parents=True)
            shutil.copyfile(root / "shared/persona/local.tmpl", target)
            reader = FixtureResolver(root)
            source = yapyon.merge(reader.source("scout", self.settings),
                                  yapyon.parse('agent:\n  persona<acme.providers.local>: {}'))
            persona = reader.resolve("scout", self.settings, source=source)["agent"]["persona"]
            self.assertEqual(persona["name"], "local")
            self.assertEqual(persona["mind"]["dialects"]["chat"]["api_uri"], "http://127.0.0.1:8000")

    def test_one_segment_include_is_rooted_at_shared(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            shutil.copytree(EXAMPLES, root)
            shutil.copyfile(root / "shared/persona/local.tmpl", root / "shared/local.tmpl")
            reader = FixtureResolver(root)
            source = yapyon.merge(reader.source("scout", self.settings),
                                  yapyon.parse('agent:\n  persona<local>: {}'))
            agent = reader.resolve("scout", self.settings, source=source)["agent"]
            self.assertEqual(agent["persona"]["name"], "local")

    def test_entries_default_does_not_redirect_existing_registrations(self):
        self.settings["paths"]["entries"] = "different-entry-container"
        agent = self.resolve("scout")["agent"]
        self.assertEqual(agent["harness"]["path"], "/example/agents/entries/scout/harness")

    def test_missing_registration_is_not_replaced_by_name_lookup(self):
        self.settings["agents"]["scout"]["path"] = "/example/agents/entries/missing-registration"
        self.assertTrue((EXAMPLES / "entries/scout/agent.cfg").is_file())
        with self.assertRaises(FileNotFoundError):
            self.resolve("scout")

    def test_invalid_path_and_nested_environment_settings_fail(self):
        for text in ('paths: None', 'paths: {shared: ""}', 'paths: {shared: None}',
                     'paths: {unknown: "x"}', 'env_vars: None',
                     'env_vars: {from_host: None}', 'env_vars: {extra: []}',
                     'env_vars: {additions: ["BAD=VALUE"]}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                registry(text)

    def test_bad_include_labels_and_document_branches_fail(self):
        for label in ((), ("..", "local"), ("persona/local",), ("", "local")):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.reader.component(label, self.settings)
        for text in ('first: {}\nsecond: {}', 'runtime: {}'):
            reader = FixtureResolver(EXAMPLES, {("invalid",): text})
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "one non-runtime branch"):
                reader.component(("invalid",), self.settings)

    def test_keyless_stays_keyless_when_default_changes(self):
        self.assertIsNone(self.resolve("scout")["agent"]["secret"])
        self.settings["defaults"]["secret"]["backend"] = "alternate_secret"
        self.assertIsNone(self.resolve("scout")["agent"]["secret"])

    def test_default_slot_follows_backend_changes(self):
        self.assertEqual(self.resolve()["agent"]["secret"]["name"], "example_secret")
        self.settings["defaults"]["secret"]["backend"] = "alternate_secret"
        self.assertEqual(self.resolve()["agent"]["secret"]["name"], "alternate_secret")

    def test_explicit_backend_does_not_follow_default_selection(self):
        self.settings["defaults"]["secret"]["backend"] = "alternate_secret"
        self.assertEqual(self.resolve("unprefixed")["agent"]["secret"]["name"], "example_secret")

    def test_root_none_is_keyed_and_uses_registered_name(self):
        secret = self.resolve("unprefixed")["agent"]["secret"]
        self.assertIsNone(secret["root"])
        self.assertEqual(secret["entry"], "unprefixed")
        self.assertEqual(shlex.split(secret["fetch"]), ["example-manager", "show", "unprefixed"])

    def test_entry_override_is_complete(self):
        secret = self.resolve()["agent"]["secret"]
        self.assertEqual(secret["root"], "agents")
        self.assertEqual(secret["entry"], "shared/team")
        self.assertEqual(shlex.split(secret["fetch"])[-1], "shared/team")

    def test_false_like_native_data_is_preserved(self):
        harness = self.resolve()["agent"]["harness"]
        native = json.loads(harness["content"])
        for key, value in {"optional": None, "retries": 0, "enabled": False, "labels": [], "extra": {}}.items():
            with self.subTest(key=key):
                self.assertEqual(harness["config_store"][key], value)
                self.assertEqual(native[key], value)
        self.assertIs(type(native["enabled"]), bool)
        self.assertIs(type(native["retries"]), int)

    def test_explicit_cleaning_changes_only_output_copy(self):
        source = self.changed('agent:\n  harness:\n    content:= y"{config_store.__not_none__().__as_json__()}"')
        harness = self.resolve(source=source)["agent"]["harness"]
        self.assertIn("optional", harness["config_store"])
        native = json.loads(harness["content"])
        self.assertNotIn("optional", native)
        self.assertEqual(native["retries"], 0)
        self.assertIs(native["enabled"], False)
        self.assertEqual(native["labels"], [])

    def test_source_roundtrip_retains_late_binding(self):
        source = self.reader.source("shared", self.settings)
        saved = source.to_source()
        restored = yapyon.parse(saved)
        for backend, endpoint in (("example_secret", "http://127.0.0.1:8000"),
                                  ("alternate_secret", "https://example.invalid")):
            with self.subTest(backend=backend):
                self.settings["defaults"]["secret"]["backend"] = backend
                env = {"AGENT_STORE_EXAMPLE_ENDPOINT": endpoint}
                original = self.resolve(source=source, env=env)
                result = self.resolve(source=restored, env=env)
                self.assertEqual(result, original)
                self.assertEqual(result["agent"]["secret"]["name"], backend)
                self.assertEqual(result["agent"]["persona"]["mind"]["endpoint"], endpoint)
        self.assertEqual(source.to_source(), saved)

    def test_no_default_and_default_overrides_is_an_error(self):
        self.settings["defaults"]["secret"]["backend"] = None
        with self.assertRaisesRegex(ValueError, "overrides require a backend"):
            self.resolve()
        self.assertIsNone(self.resolve("scout")["agent"]["secret"])
        self.assertEqual(self.resolve("unprefixed")["agent"]["secret"]["entry"], "unprefixed")

    def test_missing_secret_uses_current_default_without_source_write(self):
        source = self.reader.source("scout", self.settings)
        self.reader.fill_named(source)
        source["agent"]["secret"].remove()
        before = source.to_source()
        self.assertEqual(self.resolve("scout", source=source)["agent"]["secret"]["entry"], "agents/scout")
        self.assertEqual(source.to_source(), before)

    def test_inline_backend_requires_no_default(self):
        self.settings["defaults"]["secret"]["backend"] = None
        source = self.changed('agent:\n  secret:= {name: "inline", entry: "shared/fixed", fetch: "example-manager show shared/fixed"}')
        self.assertEqual(self.resolve(source=source)["agent"]["secret"]["entry"], "shared/fixed")

    def test_registered_rename_rebinds_name_not_directory(self):
        for old in ("unprefixed", "shared"):
            with self.subTest(old=old):
                settings = deepcopy(self.settings)
                source = self.reader.source(old, settings)
                record = settings["agents"].pop(old)
                settings["agents"]["renamed"] = record
                agent = self.reader.resolve("renamed", settings, source=source)["agent"]
                self.assertEqual(agent["name"], "renamed")
                self.assertEqual(agent["harness"]["path"], f"{record['path']}/harness")
                self.assertEqual(agent["secret"]["entry"], "renamed" if old == "unprefixed" else "shared/team")

    def test_unknown_registry_fields_and_types_fail(self):
        for text in ('extra: True', 'defaults: {unknown: {}}',
                     'defaults: {secret: {extra: None}}', 'defaults: None',
                     'agents: {scout: {path: "/x", extra: True}}',
                     'env_vars: {from_host: ["BAD=VALUE"]}', 'env_allow: []', 'env_add: []'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                registry(text)

    def test_marker_is_not_automatically_upgraded(self):
        with self.assertRaisesRegex(ValueError, "unsupported store format"):
            registry('format: "agents-yapyon-v0.1"')
        source = self.changed('agent:\n  format: "agents-yapyon-v0.1"')
        with self.assertRaisesRegex(ValueError, "source agent format"):
            self.resolve(source=source)
        source = self.changed('agent:\n  format: y"agents-yapyon-v0.6.5"')
        with self.assertRaisesRegex(ValueError, "source agent format"):
            self.resolve(source=source)

    def test_authentication_fields_preserved_without_implicit_normalization(self):
        text = ('agent:\n  harness:\n    config_store:\n      env:\n'
                '        "EXAMPLE_API_KEY": "placeholder"\n        "KEEP": "unchanged"')
        source = self.changed(text)
        before = source.to_source()
        keyed = self.resolve(source=source)["agent"]["harness"]
        self.assertEqual(keyed["auth_var"], "EXAMPLE_API_KEY")
        self.assertEqual(keyed["config_store"]["env"],
                         {"EXAMPLE_API_KEY": "placeholder", "KEEP": "unchanged"})
        keyless = self.resolve("scout", source=self.changed(text, "scout"))["agent"]["harness"]
        self.assertEqual(keyless["auth_var"], "EXAMPLE_API_KEY")
        self.assertEqual(keyless["config_store"]["env"]["EXAMPLE_API_KEY"], "placeholder")
        self.assertEqual(source.to_source(), before)

    def test_computed_agent_path_cannot_bypass_validation(self):
        source = self.changed('agent:\n  y"path": "/untrusted"')
        with self.assertRaises(ValueError):
            self.resolve(source=source)

    def test_runtime_and_agent_path_are_not_authored(self):
        for text in ('runtime: {agent_path: "/untrusted"}', 'agent: {path: "/untrusted"}',
                     'agent: {typo: "not an extension"}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.resolve(source=self.changed(text))

    def test_missing_component_is_not_materialized(self):
        source = self.changed('agent:\n  persona<persona.missing>: {}')
        path = EXAMPLES / "shared/persona/missing.tmpl"
        self.assertFalse(path.exists())
        with self.assertRaises(FileNotFoundError):
            self.resolve(source=source)
        self.assertFalse(path.exists())

    def test_component_cycle_fails(self):
        reader = FixtureResolver(EXAMPLES, {("persona", "local"): 'persona<persona.local>: {}'})
        with self.assertRaisesRegex(ValueError, "component cycle"):
            reader.resolve("scout", self.settings)

    def test_unfilled_abstract_slot_fails(self):
        source = self.changed('agent:\n  persona<>: {}')
        with self.assertRaisesRegex(ValueError, "unfilled abstract"):
            self.resolve(source=source)

    def test_disallowed_and_missing_environment_fail(self):
        source = self.changed('agent:\n  persona:\n    mind:\n      endpoint: y"{$UNLISTED_EXAMPLE}"')
        with self.assertRaises(yapyon.AkanError):
            self.resolve(source=source, env={"UNLISTED_EXAMPLE": "https://example.invalid"})
        with self.assertRaises(yapyon.AkanError):
            self.resolve(env={})

    def test_reserved_environment_remains_readable(self):
        source = self.changed('agent:\n  desc: y"{$HOME}"')
        self.assertEqual(self.resolve(source=source)["agent"]["desc"], "/example/home")

    def test_no_compatible_dialect_fails(self):
        source = self.changed('agent:\n  harness:\n    supported_dialects:= ["unavailable"]')
        with self.assertRaises((ValueError, yapyon.AkanError)):
            self.resolve(source=source)

    def test_bad_manager_entries_and_roots_fail(self):
        for value in ("", "/absolute", "-option", "x/", "x//y", "../x", "x/./y", "x\ny", "x\0y"):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                entry(value)
        for field in ("entry", "root"):
            source = self.changed(f'agent:\n  secret<>:\n    {field}: "bad/../entry"')
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "manager-relative"):
                self.resolve(source=source)

    def test_bad_registered_paths_fail(self):
        for agents in ({"scout": {"path": "relative"}},
                       {"scout": {"path": "/x/../y"}},
                       {"scout": {"path": "/x"}, "shared": {"path": "/x/sub"}}):
            with self.subTest(agents=agents), self.assertRaises(ValueError):
                registry(yapyon.dumps({"agents": agents}))

    def test_final_entry_with_punctuation_is_one_literal_argument(self):
        complete = "team/key with spaces 'quotes' ; $(literal)"
        source = self.changed("agent:\n  secret<>:\n    entry: " + yapyon.dumps(complete).strip())
        secret = self.resolve(source=source)["agent"]["secret"]
        self.assertEqual(command_argv(secret["fetch"], secret["entry"]),
                         ["example-manager", "show", complete])

    def test_plain_backend_mapping_is_not_a_default_override(self):
        source = self.changed('agent:\n  secret: {entry: "shared/only-entry"}')
        with self.assertRaisesRegex(ValueError, "incomplete secret backend"):
            self.resolve(source=source)

    def test_embedded_entry_uses_explicit_posix_quoting(self):
        complete = "team/key with space"
        self.assertEqual(command_argv("custom --entry 'team/key with space' --quiet", complete),
                         ["custom", "--entry", complete, "--quiet"])

    def test_invalid_command_quoting_and_nul_fail(self):
        for command in ("", "   ", "custom 'unterminated shared/team", "custom\0 shared/team"):
            with self.subTest(command=repr(command)), self.assertRaises(ValueError):
                command_argv(command, "shared/team")

    def test_commands_remain_inert_argument_data(self):
        source = self.changed('agent:\n  secret<>:\n    fetch: "example-manager show shared/team ; not-a-shell-command"')
        secret = self.resolve(source=source)["agent"]["secret"]
        self.assertEqual(shlex.split(secret["fetch"]),
                         ["example-manager", "show", "shared/team", ";", "not-a-shell-command"])


def main():
    global EXAMPLES
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--examples", type=Path, default=EXAMPLES, help="Synthetic fixture directory")
    parser.add_argument("--quiet", action="store_true", help="Print only the unittest result")
    args = parser.parse_args()
    EXAMPLES = args.examples.resolve()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExampleChecks)
    result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
