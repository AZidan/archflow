"""The repo mirrors framework files across two trees. They must stay identical.

CLAUDE.md states this rule; nothing enforced it until now, and the root agents/
tree drifted for exactly that reason before it was deleted.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHIPPED = REPO / "plugin" / "skills" / "archflow"
DOGFOOD = REPO / ".archflow"

# Files that legitimately live only in the shipped tree.
SHIPPED_ONLY = {"SKILL.md", "mcp-registry.yaml"}


def _relevant(root):
    out = {}
    for p in root.rglob("*"):
        if p.is_dir() or p.name == ".DS_Store":
            continue
        rel = p.relative_to(root)
        if str(rel) in SHIPPED_ONLY or rel.parts[0] in SHIPPED_ONLY:
            continue
        out[str(rel)] = p.read_bytes()
    return out


def test_mirrors_have_the_same_files():
    shipped, dogfood = _relevant(SHIPPED), _relevant(DOGFOOD)
    only_shipped = sorted(set(shipped) - set(dogfood))
    only_dogfood = sorted(set(dogfood) - set(shipped))
    assert not only_shipped, f"only in plugin/skills/archflow/: {only_shipped}"
    assert not only_dogfood, f"only in .archflow/: {only_dogfood}"


def test_mirrored_files_are_byte_identical():
    shipped, dogfood = _relevant(SHIPPED), _relevant(DOGFOOD)
    differing = sorted(k for k in set(shipped) & set(dogfood) if shipped[k] != dogfood[k])
    assert not differing, f"content differs between the mirrors: {differing}"


def test_agents_are_not_mirrored():
    """Agents live in plugin/agents/ only. A second tree is how drift starts."""
    assert not (REPO / "agents").exists(), "root agents/ tree is retired; do not recreate it"
    assert not (DOGFOOD / "agents").exists()
