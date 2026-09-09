"""Every shipped command must be findable everywhere the command surface is listed.

A command that exists but is not listed is a command nobody finds. `/archflow:contract`
had to be added to six separate lists by hand when it shipped, and nothing would have
caught a miss. These tests are that check.

The surfaces are not redundant — each is read by a different audience at a different
moment. `instructions.md` is injected into every session; `SKILL.md` is what the skill
itself advertises; `status.md` is what a user sees when they ask what to run; the README
and CLAUDE.md are what someone reads before they have a project at all.

Two further surfaces are guarded elsewhere, so do not read this list as the whole set:
`reference.md` (via `test_context_budget.test_every_agent_and_command_is_documented`)
and archflowai.dev (via `test_site_publishing.test_the_site_lists_every_shipped_command`).
Both caught `/archflow:issue` when it shipped.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMMANDS = REPO / "plugin" / "commands"

# Surfaces that must name every command. Each is (path, how the command appears).
SURFACES = [
    (REPO / ".archflow" / "instructions.md",                       "`{name}`"),
    (REPO / "plugin" / "skills" / "archflow" / "instructions.md",  "`{name}`"),
    (REPO / "plugin" / "skills" / "archflow" / "SKILL.md",         "/archflow:{name}"),
    (REPO / "plugin" / "commands" / "status.md",                   "/archflow:{name}"),
    (REPO / "CLAUDE.md",                                           "/archflow:{name}"),
    (REPO / "README.md",                                           "/archflow:{name}"),
]


def shipped():
    """Every command file the plugin ships, by bare name."""
    return sorted(p.stem for p in COMMANDS.glob("*.md"))


def test_there_are_commands_to_check():
    """Guards against a glob that silently matches nothing."""
    names = shipped()
    assert len(names) >= 10
    assert "issue" in names and "status" in names


def test_every_command_is_listed_on_every_surface():
    missing = []
    for path, form in SURFACES:
        body = path.read_text()
        for name in shipped():
            if form.format(name=name) not in body:
                missing.append(f"{path.relative_to(REPO)} does not list /archflow:{name}")
    assert not missing, "\n".join(missing)


def test_no_surface_lists_a_command_that_does_not_exist():
    """The other direction: a renamed or deleted command left behind in a list."""
    import re
    names = set(shipped())
    stale = []
    for path, _ in SURFACES:
        for found in set(re.findall(r"/archflow:([a-z][a-z-]*)", path.read_text())):
            # `archflow` is the skill's own name, invoked as /archflow:archflow.
            if found not in names and found != "archflow":
                stale.append(f"{path.relative_to(REPO)} lists /archflow:{found}, which has no command file")
    assert not stale, "\n".join(stale)


def test_every_command_has_a_description():
    """The description is what the picker shows; a command without one is unreadable."""
    for p in sorted(COMMANDS.glob("*.md")):
        head = p.read_text()[:400]
        assert head.startswith("---"), f"{p.name} has no frontmatter"
        assert "description:" in head, f"{p.name} has no description"


def test_the_readme_tree_lists_every_command_file():
    """The README's plugin tree is a map; a missing file makes it a wrong map."""
    body = (REPO / "README.md").read_text()
    # Bounded by the tree's own edges. A fixed character count starting mid-list
    # slices off the first entries and reports omissions that are not there.
    start = body.index("├── commands/")
    tree = body[start:body.index("├── scripts/", start)]
    for name in shipped():
        assert f"{name}.md" in tree, f"the README plugin tree omits commands/{name}.md"


def test_no_command_documents_the_argument_style_form():
    """CLAUDE.md: there is no `/archflow <sub>`; never document or suggest that form."""
    import re
    for p in sorted(COMMANDS.glob("*.md")):
        body = p.read_text()
        bad = re.findall(r"/archflow (?!Studio)[a-z]+", body)
        assert not bad, f"{p.name} documents the retired argument form: {bad}"
