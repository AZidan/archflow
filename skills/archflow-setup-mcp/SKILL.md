# /archflow-setup-mcp — MCP Server Setup Helper

Configure external tool MCP servers for use with Claude Code.

## Usage
```
/archflow-setup-mcp              → List available MCPs from registry
/archflow-setup-mcp [tool-name]  → Configure a specific MCP server
```

## Registry
The curated MCP registry is stored in `ref:skills/archflow-setup-mcp/mcp-registry.yaml`. Read that file to look up tool details. Edit it to add or update MCP servers.

## Invocation
When the user runs `/archflow-setup-mcp`, follow this flow exactly.

---

## Flow

### Step 1: Check If Already Configured

```bash
claude mcp list
```

Parse the output. If the requested tool is already listed:
> "[Tool] MCP is already configured. No action needed."

If not found, proceed to Step 2.

**Special case — shared MCPs**: Some tools share a server (e.g., Jira and Confluence both use Atlassian Rovo). If the registry entry has `shared_with`, check if that sibling is already configured. If so:
> "[Tool] is available through the already-configured [sibling] MCP (same server). No additional setup needed."

### Step 2: Lookup in Registry

Read `ref:skills/archflow-setup-mcp/mcp-registry.yaml` and search for the tool name (case-insensitive). If found, show:
> "[Tool] MCP uses [command/url] via [transport] transport."
> Purpose: [purpose]

If the entry has `notes`, show those too.

If not found, go to **Fallback** section.

### Step 3: Collect Credentials

For tools with `env_required`, ask the user for each variable **one at a time**:
- Show the description and help_url (if available)
- Wait for user input before proceeding to the next variable

For tools with `auth: oauth`, inform the user:
> "This MCP uses OAuth authentication. The browser will open for authorization during setup."

### Step 4: Install

Build and run the appropriate command based on transport type:

**For `stdio` transport:**
```bash
claude mcp add --transport stdio \
  --env KEY1=val1 --env KEY2=val2 \
  [tool-name] -- [command]
```

**For `http` transport with OAuth:**
```bash
claude mcp add --transport http \
  [tool-name] [url]
```

Then verify:
```bash
claude mcp get [tool-name]
```

### Step 5: Confirm

> "Configured [Tool] MCP. Restart Claude Code or run `/mcp` to verify the connection."

If the tool is `onboarding_only: true` and was set up during `/archflow-onboard`:
> "Tip: This MCP was added for onboarding import. You can remove it later with: `claude mcp remove [tool-name]`"

---

## Fallback: Tool Not in Registry

If the tool name is not in the registry:

1. Search npm for `mcp-[tool]` or `@modelcontextprotocol/server-[tool]`:
```bash
npm search mcp-[tool] --json 2>/dev/null | head -20
npm search @modelcontextprotocol/server-[tool] --json 2>/dev/null | head -20
```

2. If a package is found, show it to the user:
> "Found `[package-name]`: [description]"
> "Install this MCP? [Yes / No]"

3. If confirmed, build the stdio command:
```bash
claude mcp add --transport stdio [tool-name] -- npx -y [package-name]
```

4. If nothing found:
> "No MCP package found for '[tool]'. You can add it manually:"
> ```
> claude mcp add --transport stdio [name] -- [command]
> claude mcp add --transport http [name] [url]
> ```

---

## Listing Available MCPs

When invoked without arguments (`/archflow-setup-mcp`), read `ref:skills/archflow-setup-mcp/mcp-registry.yaml` and show the registry as a table:

```
Available MCP Servers:

| Tool         | Transport | Auth   | Purpose                              |
|--------------|-----------|--------|--------------------------------------|
| jira         | http      | oauth  | Fetch epics, stories, sprint data    |
| confluence   | http      | oauth  | Fetch Confluence pages and spaces    |
| notion       | http      | oauth  | Fetch pages and databases            |
| linear       | http      | oauth  | Fetch issues, projects, cycles       |
| github       | http      | oauth  | Fetch issues, PRs, project boards    |
| google-drive | stdio     | oauth  | Fetch Google Docs, Sheets            |
| slack        | http      | oauth  | Fetch context from channels/threads  |
| trello       | stdio     | env    | Fetch boards, lists, cards           |
| superdesign  | stdio     | —      | Generate hi-fi UI screens (Phase 2.25)|

Usage: /archflow-setup-mcp [tool-name]
```

Note: Jira and Confluence share the same Atlassian Rovo MCP server — configuring one gives access to both.

---

## Notes
- The registry file (`mcp-registry.yaml`) is the single source of truth. Edit it to add new tools.
- Package names are best-effort. If `claude mcp add` fails, try the fallback npm search.
- Some MCPs require Claude Code restart after configuration.
- OAuth MCPs will open a browser window for authorization.
