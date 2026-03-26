# /archflow setup-mcp — MCP Server Setup Helper

Configure external tool MCP servers for use with Claude Code.

## Usage
```
/archflow setup-mcp              → List available MCPs from registry
/archflow setup-mcp [tool-name]  → Configure a specific MCP server
```

## Registry
The curated MCP registry is stored in `skills/archflow/mcp-registry.yaml`. Read that file to look up tool details. Edit it to add or update MCP servers.

## Invocation
When the user runs `/archflow setup-mcp`, follow this flow exactly.

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

Read `skills/archflow/mcp-registry.yaml` and search for the tool name (case-insensitive). If found, show:
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

If the tool is `onboarding_only: true` and was set up during `/archflow onboard`:
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

When invoked without arguments (`/archflow setup-mcp`), read `skills/archflow/mcp-registry.yaml` and show the registry as a table:

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

Usage: /archflow setup-mcp [tool-name]
```

Note: Jira and Confluence share the same Atlassian Rovo MCP server — configuring one gives access to both.

---

## Multi-Agent MCP Setup

After completing the Claude Code MCP setup above, check whether other AI coding agents are active in this project by reading `skills/archflow/agent-registry.yaml`.

For each agent where `mcp_method: manual`, **first confirm the agent is present** using the same detection logic as `/archflow init` Step 5:
- Run `detection.command` if the entry has one (exit code 0 = present)
- If no command, check `detection.path` — if it exists, ask the user: "Found [path] — is [Agent Name] active in this project? [Yes / No]"
- Skip this agent if detection fails or the user answers No

If no `mcp_method: manual` agents are detected, skip this entire section silently.

For each confirmed manual agent, apply the following pattern (shown below for GitHub Copilot — repeat the same steps for any other manual agents using their `mcp_config_file` from `agent-registry.yaml`):

### GitHub Copilot (VS Code)

The tool was configured above for Claude Code via `claude mcp add`. Now guide the user to add the same server to `.vscode/mcp.json` for GitHub Copilot.

**Step 1: Check if `.vscode/mcp.json` exists**

- If it does NOT exist, offer to create it:
  ```json
  {
    "servers": {}
  }
  ```
- If it ALREADY exists, proceed to Step 2 (merge, not replace).

**Step 2: Present the exact JSON block to add**

Using the transport type and connection details from `mcp-registry.yaml`, show the user exactly what to add inside the `"servers"` object:

For a **stdio** transport tool (e.g., trello, superdesign):
```
Add this inside the "servers": {} object in .vscode/mcp.json:

"[tool-name]": {
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "[package-name]"],
  "env": {
    "[ENV_KEY]": "[value]"
  }
}
```

For an **http** transport tool (e.g., jira, notion, linear, github):
```
Add this inside the "servers": {} object in .vscode/mcp.json:

"[tool-name]": {
  "type": "http",
  "url": "[url from mcp-registry.yaml]"
}
```

Note: HTTP tools that use OAuth (e.g., Jira, Notion) will prompt for browser authorization the first time VS Code uses the server — no credentials need to be embedded in the JSON.

**Step 3: Instruct the user to reload**

```
After saving .vscode/mcp.json, reload the VS Code window:
  Command Palette → "Developer: Reload Window"

Then verify via Command Palette → "MCP: List Servers" — the server should appear.
```

### Cursor

If Cursor is detected as an active agent, guide the user to add the same server to `.cursor/mcp.json`.

**Step 1: Check if `.cursor/mcp.json` exists**

- If it does NOT exist, offer to create it:
  ```json
  {
    "mcpServers": {}
  }
  ```
  Note: Cursor uses `mcpServers` (not `servers` like VS Code).
- If it ALREADY exists, proceed to Step 2 (merge, not replace).

**Step 2: Present the exact JSON block to add**

For a **stdio** transport tool:
```
Add this inside the "mcpServers": {} object in .cursor/mcp.json:

"[tool-name]": {
  "command": "npx",
  "args": ["-y", "[package-name]"],
  "env": {
    "[ENV_KEY]": "[value]"
  }
}
```

For an **http** transport tool:
```
Add this inside the "mcpServers": {} object in .cursor/mcp.json:

"[tool-name]": {
  "url": "[url from mcp-registry.yaml]"
}
```

**Step 3: Instruct the user to restart**

```
After saving .cursor/mcp.json, completely quit and reopen Cursor.
MCP servers only load at startup — a window reload is not sufficient.

Then verify via Cursor Settings → MCP — the server should appear with a green indicator.
```

---

**Skipping this section:** If no agents with `mcp_method: manual` are detected in `agent-registry.yaml`, skip this entire section silently.

---

## Notes
- `mcp-registry.yaml` is the source of truth for MCP server details (transport, URLs, env vars).
- `agent-registry.yaml` is the source of truth for which agents are present and how they install MCPs.
- Package names are best-effort. If `claude mcp add` fails, try the fallback npm search.
- Some MCPs require Claude Code restart after configuration.
- OAuth MCPs will open a browser window for authorization (Claude Code) or VS Code authorization prompt (GitHub Copilot).
