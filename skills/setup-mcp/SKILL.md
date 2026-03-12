# /setup-mcp — MCP Server Setup Helper

Configure external tool MCP servers for use with Claude Code.

## Usage
```
/setup-mcp              → List available MCPs from registry
/setup-mcp [tool-name]  → Configure a specific MCP server
```

## Invocation
When the user runs `/setup-mcp`, follow this flow exactly.

---

## Flow

### Step 1: Check If Already Configured

```bash
claude mcp list
```

Parse the output. If the requested tool is already listed:
> "[Tool] MCP is already configured. No action needed."

If not found, proceed to Step 2.

### Step 2: Lookup in Curated Registry

Search the registry below for the tool name (case-insensitive). If found, show:
> "[Tool] MCP uses [command/url] via [transport] transport."
> Purpose: [purpose]

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

If the tool is `onboarding_only: true` and was set up during `/onboard`:
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

## Curated MCP Registry

### jira
- **Name**: Jira
- **Transport**: stdio
- **Command**: `npx -y @anthropic/claude-code-jira`
- **Env Required**:
  - `JIRA_API_TOKEN`: API token — get at https://id.atlassian.com/manage-profile/security/api-tokens
  - `JIRA_DOMAIN`: e.g., company.atlassian.net
  - `JIRA_EMAIL`: Jira account email
- **Purpose**: Fetch epics, stories, and sprint data by link
- **Onboarding Only**: true

### notion
- **Name**: Notion
- **Transport**: http
- **URL**: `https://mcp.notion.com/mcp`
- **Auth**: oauth
- **Purpose**: Fetch pages and databases by link
- **Onboarding Only**: true

### linear
- **Name**: Linear
- **Transport**: http
- **URL**: `https://mcp.linear.app/sse`
- **Auth**: oauth
- **Purpose**: Fetch issues, projects, and cycles by link
- **Onboarding Only**: true

### github
- **Name**: GitHub
- **Transport**: http
- **URL**: `https://api.githubcopilot.com/mcp/`
- **Auth**: oauth
- **Purpose**: Fetch issues, PRs, project boards
- **Onboarding Only**: false

### confluence
- **Name**: Confluence
- **Transport**: stdio
- **Command**: `npx -y @anthropic/claude-code-confluence`
- **Env Required**:
  - `CONFLUENCE_API_TOKEN`: API token — get at https://id.atlassian.com/manage-profile/security/api-tokens
  - `CONFLUENCE_DOMAIN`: Your Confluence domain
  - `CONFLUENCE_EMAIL`: Confluence account email
- **Purpose**: Fetch documentation pages by link
- **Onboarding Only**: true

### google-drive
- **Name**: Google Drive
- **Transport**: stdio
- **Command**: `npx -y @anthropic/claude-code-google-drive`
- **Auth**: oauth
- **Purpose**: Fetch Google Docs, Sheets by link
- **Onboarding Only**: true

### slack
- **Name**: Slack
- **Transport**: http
- **URL**: `https://api.slack.com/mcp`
- **Auth**: oauth
- **Purpose**: Fetch context from channels and threads
- **Onboarding Only**: true

### trello
- **Name**: Trello
- **Transport**: stdio
- **Command**: `npx -y @modelcontextprotocol/server-trello`
- **Env Required**:
  - `TRELLO_API_KEY`: API key — get at https://trello.com/power-ups/admin
  - `TRELLO_TOKEN`: Auth token
- **Purpose**: Fetch boards, lists, and cards
- **Onboarding Only**: true

---

## Listing Available MCPs

When invoked without arguments (`/setup-mcp`), show the registry as a table:

```
Available MCP Servers:

| Tool         | Transport | Auth   | Purpose                              |
|--------------|-----------|--------|--------------------------------------|
| jira         | stdio     | env    | Fetch epics, stories, sprint data    |
| notion       | http      | oauth  | Fetch pages and databases            |
| linear       | http      | oauth  | Fetch issues, projects, cycles       |
| github       | http      | oauth  | Fetch issues, PRs, project boards    |
| confluence   | stdio     | env    | Fetch documentation pages            |
| google-drive | stdio     | oauth  | Fetch Google Docs, Sheets            |
| slack        | http      | oauth  | Fetch context from channels/threads  |
| trello       | stdio     | env    | Fetch boards, lists, cards           |

Usage: /setup-mcp [tool-name]
```

---

## Notes
- Package names in this registry are best-effort. If `claude mcp add` fails, try the fallback npm search.
- Some MCPs require Claude Code restart after configuration.
- OAuth MCPs will open a browser window for authorization.
