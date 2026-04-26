#!/usr/bin/env bash
# Apify MCP server launcher.
#
# Spawns @apify/actors-mcp-server only if APIFY_TOKEN is set. Without a
# token, exec a no-op MCP-shaped process so the plugin install does not
# error and the rest of the plugin still works.
set -e

if [ -z "${APIFY_TOKEN:-}" ]; then
  # Idle until killed; expose no MCP tools.
  exec node -e "process.stdin.resume()"
fi

exec npx -y @apify/actors-mcp-server
