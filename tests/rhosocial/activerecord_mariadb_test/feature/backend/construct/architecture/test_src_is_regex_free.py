# tests/rhosocial/activerecord_mariadb_test/feature/backend/construct/architecture/test_src_is_regex_free.py
"""``src`` must never reach for the standard library's regular-expression module.

This backend's parsers read server spellings -- a declared column type, a type's
charset/collation, a spatial reference system, a server version -- and those
grammars are small and fixed. They are written as character scans
(``_scan.py``) rather than patterns, and the project rule is that ``src`` keeps
no pattern engine at all: no ``import re``, no ``from re import ...``, no
``re.<attribute>``. Tests may still use patterns, but only to assert the SQL a
formatter generated; production code may not.

Two independent checks run, because each misses what the other catches: an
``ast`` walk finds every import and every module reference even inside code the
text scan would have to tokenise, and a line scan finds a bare ``re.`` in
comments or strings where a future reader might reintroduce the habit. The
third test proves neither scan is vacuous.
"""

import ast
import pathlib
import re as regex_module
import textwrap

import rhosocial.activerecord.backend.impl.mariadb as mariadb_package

#: The backend package this guard scans -- everything that ships as ``src``.
#: ``__path__`` rather than ``__file__``: the editable install resolves the
#: package through a PEP 420 namespace finder, where ``__file__`` is ``None``.
SRC_ROOT = pathlib.Path(next(iter(mariadb_package.__path__)))

#: The text shape of a module use: the bare name ``re`` followed by a dot.
#: ``\b`` keeps ``core.next`` and ``store.data`` from reading as a match.
RE_ATTRIBUTE_TOKEN = regex_module.compile(r"\bre\.")


def _src_files():
    """Every Python module under :data:`SRC_ROOT`, in a stable order."""
    return sorted(SRC_ROOT.rglob("*.py"))


def _re_imports(tree):
    """Return ``[(lineno, statement)]`` for imports of the ``re`` module."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "re" or alias.name.startswith("re."):
                    found.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "re" or module.startswith("re."):
                names = ", ".join(alias.name for alias in node.names)
                found.append((node.lineno, f"from {module} import {names}"))
    return found


def _re_references(tree):
    """Return ``[(lineno, expression)]`` for every bare use of the name ``re``.

    A module use is a ``Name`` node: ``re.compile(...)`` reaches the attribute
    through it, and so does ``re`` passed as a value. Matching the name catches
    both without having to enumerate attributes.
    """
    return [
        (node.lineno, node.id)
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "re"
    ]


def _scan(paths):
    """Return ``(imports, references, text_tokens)`` found across ``paths``.

    ``imports`` and ``references`` are ``(path, lineno, detail)`` triples from
    the ``ast`` walk; ``text_tokens`` are ``(path, lineno, line)`` triples from
    the line scan. Paths are absolute so a failure names the file to open.
    """
    imports = []
    references = []
    text_tokens = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for lineno, statement in _re_imports(tree):
            imports.append((path, lineno, statement))
        for lineno, name in _re_references(tree):
            references.append((path, lineno, name))
        for lineno, line in enumerate(source.splitlines(), start=1):
            if RE_ATTRIBUTE_TOKEN.search(line):
                text_tokens.append((path, lineno, line.strip()))
    return imports, references, text_tokens


def test_the_guard_scans_the_shipped_source_tree():
    """The scan must not be pointing at an empty tree or the wrong package."""
    files = _src_files()
    assert files, f"no modules found under {SRC_ROOT}"
    parsed = {path.name for path in files}
    assert "type_parser.py" in parsed
    assert "_scan.py" in parsed


def test_src_does_not_import_the_re_module():
    """No module in ``src`` may import ``re``, under any alias."""
    imports, _, _ = _scan(_src_files())
    assert not imports, (
        "These modules import the standard library's regular-expression "
        f"module: {imports}. Reimplement the match as a character scan; "
        "``_scan.py`` holds the shared helpers."
    )


def test_src_does_not_address_the_re_module():
    """No module in ``src`` may use the name ``re`` as a value or attribute base."""
    _, references, _ = _scan(_src_files())
    assert not references, (
        f"These modules reference the bare name ``re``: {references}. A pattern "
        "engine has no place in the read-direction parsers; use ``_scan.py``."
    )


def test_src_text_has_no_re_attribute_tokens():
    """No source line in ``src`` may spell ``re.``, even in a comment or string."""
    _, _, text_tokens = _scan(_src_files())
    assert not text_tokens, (
        f"These lines spell a regular-expression-module attribute: {text_tokens}. "
        "If the line is a comment or docstring, describe the scan instead of "
        "naming a pattern engine the module is not allowed to use."
    )


def test_the_guard_reports_a_synthetic_violation(tmp_path):
    """The three checks are not vacuous: a planted module fails all of them.

    Without this, a bug in the scanners would make the guard pass silently for
    a backend that had gone back to patterns.
    """
    offender = tmp_path / "offending.py"
    offender.write_text(
        textwrap.dedent("""
            import re

            def compiled(text):
                return re.compile(r"^[A-Z]+")
            """),
        encoding="utf-8",
    )

    imports, references, text_tokens = _scan([offender])
    assert imports, "the import scan missed ``import re``"
    assert references, "the reference scan missed ``re.compile``"
    assert text_tokens, "the text scan missed the literal ``re.`` token"
