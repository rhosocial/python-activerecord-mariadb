import codecs
import os
import re
from setuptools import setup, find_namespace_packages

def read(rel_path):
    """Read file."""
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r', 'utf-8') as fp:
        return fp.read()

def find_version(rel_path):
    """Get version from __init__.py file."""
    init_file = read(rel_path)
    pattern = r'^__version__\s*=\s*"((?:[1-9]\d*!)?\d+(?:\.\d+)*(?:[-._]?(?:a|alpha|b|beta|rc|pre|preview)(?:[-._]?\d+)?)?(?:\.post(?:0|[1-9]\d*))?(?:\.dev(?:0|[1-9]\d*))?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?)"$'
    version_match = re.search(pattern, init_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    name="rhosocial_activerecord_mariadb",
    version=find_version("src/rhosocial/activerecord/backend/impl/mariadb/__init__.py"),
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src", include=['rhosocial.activerecord.backend.impl.mariadb', 'rhosocial.activerecord.backend.impl.mariadb.*']),
    python_requires=">=3.8",
    install_requires=[
        "rhosocial-activerecord>=1.0.0,<2.0.0",
        "mariadb>=1.1.0",
    ],
    extras_require={
        "pooling": ["DBUtils>=3.0.0"],
        "test": [
            "pytest>=7.0.0",
            "coverage>=7.0.0",
        ],
        "dev": [
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    namespace_packages=['rhosocial', 'rhosocial.activerecord', 'rhosocial.activerecord.backend', 'rhosocial.activerecord.backend.impl'],
)