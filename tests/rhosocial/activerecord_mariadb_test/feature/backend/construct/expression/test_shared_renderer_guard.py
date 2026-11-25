# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/expression/test_shared_renderer_guard.py
"""No private renderer is shared between public formatters.

A formatter owns its expression kind: it reads that node's fields, applies
that node's capability gates and assembles its SQL. A private ``_render_*`` /
``_format_*`` method called from two or more public ``format_*`` methods in
the same class puts part of that work back outside both formatters, which is
the defect this guard exists to catch -- the gates and the assembly drift back
into one place that neither formatter can be read on its own.

What may stay shared is a value-level concern only: a tiny utility that takes
already-settled values (strings, numbers, tuples, a list of rendered entries)
and returns a string or ``(sql, params)``. It must not take a statement node,
must not read a capability probe and must not raise ``UnsupportedFeatureError``
itself. A helper that renders a *sub-node* -- one column definition, say -- is
the same shape of concern and qualifies on the same terms.

The allow-list is asserted to be exactly the set that exists in both
directions: a new shared renderer fails, and a stale entry fails too, so the
reasons cannot rot into permission for something that was deleted.
"""

import ast
import pathlib
from typing import Dict, Iterable, List, Set, Tuple

import rhosocial.activerecord.backend.impl.mariadb.mixins as mixins_package

#: Root of the package this guard scans.
MIXINS_ROOT = pathlib.Path(mixins_package.__file__).parent

#: The only private renderers two public formatters may share, each with the
#: reason it is a value-level utility rather than a shared renderer.
#:
#: Reasons must begin with ``value-level`` or ``sub-node``; the third test
#: below enforces that, so an entry cannot be added without saying which of
#: the two permitted concerns it is.
ALLOWED_SHARED_HELPERS: Dict[Tuple[str, str], str] = {
    ("MariaDBAdminMixin", "_format_accounts"): (
        "value-level: joins ``'user'@'host'`` account values, quoting the two "
        "fields; takes no statement node and reads no capability probe."
    ),
    ("MariaDBAdminMixin", "_format_privileges"): (
        "value-level: joins privilege values, quoting their optional column "
        "lists; takes no statement node and reads no capability probe."
    ),
    ("MariaDBRoutineMixin", "_format_routine_param"): (
        "value-level: renders one parameter definition from a plain string or "
        "a ``(mode, name, type)`` tuple; takes no statement node and reads no "
        "capability probe."
    ),
    ("MariaDBPartitionMixin", "_format_partition_key_list"): (
        "value-level: joins the already-rendered key entries of one list "
        "through their own ``to_sql``; takes no statement node and reads no "
        "capability probe."
    ),
    ("MariaDBTypeSupportMixin", "_format_mariadb_integer"): (
        "value-level: appends ``UNSIGNED`` / ``ZEROFILL`` to an already-rendered "
        "type word and checks the flag's shape; takes no statement node and "
        "reads no capability probe."
    ),
    ("MariaDBTypeSupportMixin", "_format_mariadb_spatial"): (
        "value-level: appends ``REF_SYSTEM_ID`` to an already-rendered spatial "
        "type word; takes no statement node and reads no capability probe."
    ),
}

#: Helpers that were removed because they were shared renderers. They must not
#: come back, even if only one formatter would call them.
REMOVED_SHARED_RENDERERS = {
    ("MariaDBRoutineMixin", "_render_create_function_statement"),
    ("MariaDBRoutineMixin", "_render_drop_function_statement"),
    ("MariaDBJSONMixin", "_format_json_table_body"),
    ("MariaDBPartitionMixin", "_format_partition_action"),
}

#: The two kinds of concern a shared private helper may be.
PERMITTED_REASON_PREFIXES = ("value-level", "sub-node")

#: Class body methods the scanner treats as public formatters.
FORMATTER_PREFIX = "format_"

#: Class body methods the scanner treats as private renderers.
RENDERER_PREFIXES = ("_render_", "_format_")


def _methods(cls: ast.ClassDef) -> Dict[str, ast.FunctionDef]:
    """Return the class-body methods, keyed by name.

    Nested ``def`` bodies are deliberately not walked: a closure inside one
    formatter is not a method of the class.
    """
    return {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}


def _shared_renderers_in(paths: Iterable[pathlib.Path]) -> Dict[Tuple[str, str], List[str]]:
    """Return ``{(class name, helper name): [formatter names]}`` for shared helpers.

    A helper is shared when two or more class-body methods whose name starts
    with ``format_`` call it through ``self``. Calls through any other object
    are not counted; the question is whether the class's own formatters share
    one renderer.
    """
    shared: Dict[Tuple[str, str], List[str]] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            methods = _methods(cls)
            formatters = [name for name in methods if name.startswith(FORMATTER_PREFIX)]
            renderers = {name for name in methods if name.startswith(RENDERER_PREFIXES)}
            callers: Dict[str, Set[str]] = {}
            for formatter in formatters:
                for call in ast.walk(methods[formatter]):
                    if not isinstance(call, ast.Call):
                        continue
                    func = call.func
                    if not isinstance(func, ast.Attribute):
                        continue
                    if not isinstance(func.value, ast.Name) or func.value.id != "self":
                        continue
                    if func.attr not in renderers:
                        continue
                    callers.setdefault(func.attr, set()).add(formatter)
            for helper, names in callers.items():
                if len(names) >= 2:
                    shared[(cls.name, helper)] = sorted(names)
    return shared


def _scan_package() -> Dict[Tuple[str, str], List[str]]:
    """Scan every module under :data:`MIXINS_ROOT`."""
    return _shared_renderers_in(sorted(MIXINS_ROOT.rglob("*.py")))


def _defined_renderer_names() -> Set[Tuple[str, str]]:
    """Return every ``(class name, private renderer name)`` defined in the package."""
    defined: Set[Tuple[str, str]] = set()
    for path in sorted(MIXINS_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for name in _methods(cls):
                if name.startswith(RENDERER_PREFIXES):
                    defined.add((cls.name, name))
    return defined


def test_no_private_renderer_is_shared_outside_the_allow_list():
    """A new shared renderer fails here, naming the class and its callers."""
    shared = _scan_package()
    offenders = {
        helper: callers
        for helper, callers in shared.items()
        if helper not in ALLOWED_SHARED_HELPERS
    }
    assert not offenders, (
        "These private renderers are shared by two or more public formatters, "
        "so their SQL assembly and capability gates live outside each formatter: "
        f"{sorted(offenders)}. Inline the body into each formatter that needs it; "
        "a value-level helper must take primitives only and gate nothing."
    )


def test_the_allow_list_is_exactly_the_set_that_exists():
    """A stale allow-list entry fails here, so the reasons cannot outlive the helper."""
    shared = _scan_package()
    stale = sorted(set(ALLOWED_SHARED_HELPERS) - set(shared))
    assert not stale, (
        "The allow-list names helpers that are no longer shared by two or more "
        f"formatters: {stale}. Delete the entry; the list must describe what exists."
    )


def test_every_allow_listed_reason_names_a_permitted_kind():
    """A reason must say which of the two permitted concerns the helper is."""
    unnamed = sorted(
        helper
        for helper, reason in ALLOWED_SHARED_HELPERS.items()
        if reason.split(":", 1)[0].strip().lower() not in PERMITTED_REASON_PREFIXES
    )
    assert not unnamed, (
        "These allow-list entries do not begin with a permitted kind "
        f"({PERMITTED_REASON_PREFIXES}): {unnamed}. A statement node's renderer "
        "has no permitted kind and must not be allow-listed at all."
    )


def test_the_removed_shared_renderers_stay_deleted():
    """The helpers that only existed to share assembly must not come back."""
    defined = _defined_renderer_names()
    resurrected = sorted(REMOVED_SHARED_RENDERERS & defined)
    assert not resurrected, (
        "These shared renderers were inlined into their formatters and deleted: "
        f"{resurrected}. Build the SQL inside each formatter instead."
    )


def test_the_scanner_detects_a_shared_renderer(tmp_path):
    """The scan itself is not vacuous: a synthetic shared renderer is reported.

    Without this, a bug in the scanner would make the first three tests pass
    silently for a backend that had gone back to one shared renderer.
    """
    source = """
class SyntheticMixin:
    def _render_shared(self, expr):
        return "x", ()

    def format_first(self, expr):
        return self._render_shared(expr)

    def format_second(self, expr):
        return self._render_shared(expr)

    def _format_single_use(self, value):
        return str(value)

    def format_third(self, expr):
        return self._format_single_use(expr.value)
"""
    path = tmp_path / "synthetic_mixin.py"
    path.write_text(source, encoding="utf-8")

    shared = _shared_renderers_in([path])

    assert shared == {("SyntheticMixin", "_render_shared"): ["format_first", "format_second"]}
