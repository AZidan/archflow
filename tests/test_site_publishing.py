"""Guards on what reaches archflowai.dev.

`docs/` is the GitHub Pages source, so anything reachable there is published. It
used to be allow-by-default with a hand-maintained deny list in `_config.yml`,
which failed twice: the list still excluded a file that no longer existed, and a
working document naming every known security finding was committed and would have
rendered at archflowai.dev/remediation-backlog on the next build.

The site is now deny-by-default. Internal work lives in `docs/internal/`, excluded
wholesale, and these tests fail if anything escapes.
"""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"

# The complete published surface. Adding to it is a deliberate act.
PUBLISHED_MD = {"guides"}


def excludes():
    return set(yaml.safe_load((DOCS / "_config.yml").read_text()).get("exclude") or [])


def test_internal_is_excluded_wholesale():
    assert "internal" in excludes(), "docs/internal/ must be excluded from the site build"


def test_no_per_file_exclude_list():
    """A per-file list has to be edited by whoever adds a doc. It drifted before."""
    per_file = [e for e in excludes() if str(e).endswith(".md")]
    assert not per_file, (
        f"per-file excludes are back: {per_file}. Move the file into docs/internal/ instead — "
        "a list only protects the files someone remembered to add."
    )


def test_no_stray_markdown_at_the_docs_root():
    """Anything here publishes. There is no legitimate case for it."""
    stray = sorted(p.name for p in DOCS.glob("*.md"))
    assert not stray, (
        f"markdown at docs/ root would publish to archflowai.dev: {stray}. "
        "Move it to docs/internal/."
    )


def test_only_the_guides_directory_publishes_markdown():
    ex = excludes()
    rendered = []
    for path in DOCS.rglob("*.md"):
        rel = path.relative_to(DOCS)
        top = rel.parts[0]
        if top in ex or top in {"_site", "vendor", ".bundle"}:
            continue
        rendered.append(str(rel))
    unexpected = [r for r in rendered if Path(r).parts[0] not in PUBLISHED_MD]
    assert not unexpected, f"these would publish: {sorted(unexpected)}"


def test_internal_docs_are_not_tracked_by_default():
    """New working docs must be ignored without anyone remembering.

    Three design records predate this and are explicitly un-ignored; everything
    else under docs/internal/ stays out of git.
    """
    gitignore = (REPO / ".gitignore").read_text()
    assert "docs/internal/*" in gitignore, "docs/internal/ is not ignored by default"
    exceptions = [l.strip() for l in gitignore.splitlines() if l.strip().startswith("!docs/internal/")]
    assert len(exceptions) <= 5, (
        f"{len(exceptions)} exceptions to the internal-docs ignore. Each one is a file that "
        "will be committed; keep the list short and deliberate."
    )


def test_the_security_backlog_is_not_tracked():
    """It names every known weakness, with reproduction detail."""
    import subprocess
    out = subprocess.run(["git", "ls-files", "docs/"], cwd=REPO,
                         capture_output=True, text=True).stdout
    for sensitive in ("remediation-backlog", "agent-definitions-audit",
                      "security-audit-remediation"):
        assert sensitive not in out, f"{sensitive} is tracked in git"
