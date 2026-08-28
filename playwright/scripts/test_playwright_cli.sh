#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
wrapper="${script_dir}/playwright_cli.sh"
temp_dir="$(mktemp -d)"
trap 'rm -rf "${temp_dir}"' EXIT

mock_bin="${temp_dir}/bin"
mkdir -p "${mock_bin}"
mock_output="${temp_dir}/npx-args"

cat >"${mock_bin}/npx" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$@" >"${MOCK_NPX_OUTPUT}"
MOCK
chmod +x "${mock_bin}/npx"

run_wrapper() {
  PATH="${mock_bin}:/usr/bin:/bin" MOCK_NPX_OUTPUT="${mock_output}" "$wrapper" "$@"
}

assert_args() {
  local expected="$1"
  local actual
  actual="$(cat "${mock_output}")"
  if [[ "$actual" != "$expected" ]]; then
    echo "Unexpected wrapper arguments" >&2
    diff -u <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") >&2 || true
    exit 1
  fi
}

PLAYWRIGHT_CLI_SESSION=env-session run_wrapper snapshot
assert_args $'--yes\n--package\n@playwright/cli\nplaywright-cli\n--session\nenv-session\nsnapshot'

PLAYWRIGHT_CLI_SESSION=env-session run_wrapper --session explicit snapshot
assert_args $'--yes\n--package\n@playwright/cli\nplaywright-cli\n--session\nexplicit\nsnapshot'

PLAYWRIGHT_CLI_SESSION=env-session run_wrapper -s=short snapshot
assert_args $'--yes\n--package\n@playwright/cli\nplaywright-cli\n-s=short\nsnapshot'

PLAYWRIGHT_CLI_PACKAGE='@playwright/cli@1.2.3' run_wrapper --help
assert_args $'--yes\n--package\n@playwright/cli@1.2.3\nplaywright-cli\n--help'

echo "playwright_cli.sh tests passed"
