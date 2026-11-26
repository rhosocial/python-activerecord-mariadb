# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/dialect/test_support_switches_take_no_arguments.py
"""``supports_*`` is a support switch: no arguments, one bool.

A capability flag answers "does this dialect configuration have capability k",
so its only input is the dialect instance, and its only answer is a bool.
Anything that needs a name or a kind -- or answers with a catalogue -- is
either a separate switch over a closed vocabulary, a ``suggest_*`` value or a
format-time validation (``validate_*``) -- never an argument to ``supports_*``
and never a non-bool annotation.

This walks the whole MariaDB backend source tree, not just the dialect module,
because a ``supports_*`` that grows a parameter or answers with a mapping in a
mixin, a protocol stub or a CLI helper is exactly the drift the rule forbids.

The same tree is walked for the other half of the rule: no class ending in
``Dialect`` may inherit a ``*Support`` protocol. A ``runtime_checkable``
Protocol matches structurally, so inheriting one adds only ellipsis stubs and
turns ``isinstance`` into a claim the class does not actually keep.
"""
import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[7]


def _source_files():
    """Every Python module in this repository's ``src`` tree."""
    root = _REPO_ROOT / "src"
    files = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _required_arguments(func: ast.FunctionDef):
    """Parameters that must be passed, excluding ``self``."""
    args = func.args
    positional = list(args.args)
    required = positional[1 : len(positional) - len(args.defaults)]
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            required.append(arg)
    return [a.arg for a in required]


def _annotates_bool(func: ast.FunctionDef):
    """Why a switch's annotation is not ``-> bool``, or ``None`` when it is.

    A switch declares one answer, so the annotation is part of the rule rather
    than decoration: returning a mapping or an info record from ``supports_*``
    is a catalogue wearing a switch's name. The quoted form ``-> "bool"`` is
    the same declaration under postponed evaluation and is accepted.
    """
    annotation = func.returns
    if annotation is None:
        return "has no return annotation (expected -> bool)"
    if isinstance(annotation, ast.Name) and annotation.id == "bool":
        return None
    if isinstance(annotation, ast.Constant) and annotation.value == "bool":
        return None
    return f"does not return bool (annotated {ast.unparse(annotation)})"


def _offenders(tree, label):
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not item.name.startswith("supports_"):
                continue
            missing = _required_arguments(item)
            if missing:
                found.append(f"{label}:{item.lineno} {item.name}({', '.join(missing)})")
            else:
                annotation_offence = _annotates_bool(item)
                if annotation_offence:
                    found.append(f"{label}:{item.lineno} {item.name} {annotation_offence}")
    return found


def _tree_offenders():
    found = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.extend(_offenders(tree, path.name))
    return found


def _base_name(base):
    """The written name of a base expression, or ``None``.

    Only names matter here: a ``Name`` (``ReturningSupport``) or an
    ``Attribute`` (``protocols.ReturningSupport``) spells the protocol; a
    subscript or a call is not a class name and cannot end in ``Support``.
    """
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _protocol_base_offenders(tree, label):
    """Dialects that inherit a ``*Support`` protocol, rendered ``label:line``.

    A ``runtime_checkable`` Protocol is satisfied structurally, so inheriting
    it adds nothing but its ellipsis-bodied members -- and makes ``isinstance``
    answer ``True`` for a class with no implementation behind the members. The
    protocol belongs in an ``isinstance`` target and a test, never in a
    dialect's bases; the mixins are what implement it.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Dialect"):
            continue
        for base in node.bases:
            name = _base_name(base)
            if name is not None and name.endswith("Support"):
                found.append(f"{label}:{node.lineno} {node.name}({name})")
    return found


def _tree_protocol_base_offenders():
    found = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.extend(_protocol_base_offenders(tree, path.name))
    return found


def test_no_support_switch_takes_a_required_argument():
    offenders = _tree_offenders()
    assert not offenders, "\n".join(offenders)


def test_the_scan_reaches_the_source_tree():
    files = _source_files()
    assert len(files) > 50, f"only {len(files)} source files were scanned"


def test_the_scan_flags_a_planted_violation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, name):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_flags_a_planted_keyword_only_violation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, *, kind):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_accepts_a_defaulted_parameter(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, name=None) -> bool:\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")


def test_the_scan_flags_a_non_bool_annotation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "from typing import Dict\n"
        "class P:\n"
        "    def supports_thing(self) -> Dict[str, bool]:\n"
        "        return {}\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, "probe")
    assert offenders and "does not return bool" in offenders[0]


def test_the_scan_flags_an_unannotated_switch(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, "probe")
    assert offenders and "no return annotation" in offenders[0]


def test_the_scan_accepts_a_quoted_bool_annotation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        'class P:\n    def supports_thing(self) -> "bool":\n        return False\n',
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")


def test_no_dialect_inherits_a_support_protocol():
    """A protocol in a dialect's bases is a lie waiting to be told."""
    offenders = _tree_protocol_base_offenders()
    assert not offenders, "\n".join(offenders)


def test_the_protocol_base_scan_reaches_the_source_tree():
    files = _source_files()
    assert len(files) > 50, f"only {len(files)} source files were scanned"


def test_the_protocol_base_scan_flags_a_planted_violation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "from rhosocial.activerecord.backend.dialect.protocols import (\n"
        "    ReturningSupport,\n"
        ")\n"
        "\n"
        "class ProbeDialect(ReturningSupport):\n"
        "    pass\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _protocol_base_offenders(tree, "probe")
    assert offenders, "a dialect inheriting a protocol was not flagged"
    assert "ProbeDialect(ReturningSupport)" in offenders[0]


def test_the_protocol_base_scan_flags_a_qualified_base(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class ProbeDialect(protocols.ReturningSupport):\n"
        "    pass\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _protocol_base_offenders(tree, "probe")


def test_the_protocol_base_scan_accepts_a_clean_control(tmp_path):
    """A mixin may inherit a protocol; only a ``*Dialect`` may not."""
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class ProbeMixin(ReturningSupport):\n"
        "    pass\n"
        "\n"
        "class ProbeDialect(ProbeMixin, SQLDialectBase):\n"
        "    pass\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _protocol_base_offenders(tree, "probe")
