#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_node_version=$(cat "$task_root/.node-version")
task_node_bin="$task_root/.toolchain/node-v${task_node_version}-linux-x64/bin"
if [[ -x "$task_node_bin/node" ]]; then
  export PATH="$task_node_bin:$PATH"
fi
if [[ "$(node --version)" != "v${task_node_version}" ]]; then
  echo "Node ${task_node_version} is required; run make setup." >&2
  exit 1
fi
exec "$@"
