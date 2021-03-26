"""Nox configuration
"""

import nox

SOURCES = ["src"]


@nox.session
def flake8(session):
    """Lint code with Flake8."""
    session.install("flake8")
    session.run("flake8", *SOURCES)


@nox.session
def black(session):
    """Check code formatting with black."""
    session.install("black")
    session.run("black", "--check", *SOURCES)


@nox.session
def isort(session):
    """Check import sorting with isort."""
    session.install("isort")
    session.run("isort", "--check", *SOURCES)


@nox.session(python=["3.7", "3.8", "3.9"])
def test(session):
    session.create_tmp()
    session.install("-e", ".[testing]")
    tests = session.posargs or ["tests/"]
    session.run("pytest", *tests)
