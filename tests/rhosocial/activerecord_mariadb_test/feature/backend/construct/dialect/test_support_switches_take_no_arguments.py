# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/dialect/test_support_switches_take_no_arguments.py
"""``supports_*`` is a support switch: no arguments, one bool.

A capability flag answers "does this dialect configuration have capability k",
so its only input is the dialect instance. Anything that needs a name or a kind
is either a separate switch over a closed vocabulary or a format-time
validation (``validate_*``) -- never an argument to ``supports_*``.

This walks the whole MariaDB backend source tree, not just the dialect module,
because a ``supports_*`` that grows a parameter in a mixin, a protocol stub or
a CLI helper is exactly the drift the rule forbids.
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
    return found


def _tree_offenders():
    found = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.extend(_offenders(tree, path.name))
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
        "    def supports_thing(self, name=None):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")
