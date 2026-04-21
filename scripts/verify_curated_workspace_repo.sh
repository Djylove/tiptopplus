#!/usr/bin/env bash

set -euo pipefail

pass() {
  echo "PASS: $1"
}

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "not inside a git work tree"
fi

repo_root=$(git rev-parse --show-toplevel)
repo_root=$(cd "$repo_root" && pwd -P)
cwd=$(pwd -P)

if [[ "$cwd" != "$repo_root" ]]; then
  fail "run this script from the workspace root: $repo_root"
fi

pass "inside curated workspace git repo"

branch=$(git branch --show-current)
if [[ "$branch" != "main" ]]; then
  fail "expected current branch main, got ${branch:-<detached>}"
fi
pass "current branch is main"

origin_url=$(git remote get-url origin 2>/dev/null || true)
if [[ -z "$origin_url" ]]; then
  fail "origin remote is not configured"
fi

expected_remote_regex=${TIPTOPPLUS_EXPECTED_REMOTE_REGEX:-Djylove/tiptopplus(\.git)?$}
if [[ ! "$origin_url" =~ $expected_remote_regex ]]; then
  fail "origin remote does not match ${expected_remote_regex}: $origin_url"
fi
pass "origin remote matches expected tiptopplus pattern"

required_files=(
  "README.md"
  "WORKSPACE-SERVICES.md"
  ".planning/PROJECT.md"
  "WORKSPACE-BOOTSTRAP.md"
)

for required_file in "${required_files[@]}"; do
  if [[ ! -e "$required_file" ]]; then
    fail "missing required file: $required_file"
  fi
  pass "required file exists: $required_file"
done

ignored_paths=(
  "sam3"
  "Fast-FoundationStereo"
  "FoundationStereo"
  "M2T2"
  "droid-sim-evals"
  "tiptop/curobo"
  "tiptop/cutamp"
  "tiptop/.pixi"
  "tiptop/tiptop_h5_scene4_capfix3"
  "tiptop/tiptop_server_outputs"
  "tmp_scene4_frames"
)

for ignored_path in "${ignored_paths[@]}"; do
  if ! git check-ignore "$ignored_path" >/dev/null 2>&1; then
    fail "expected ignored path is not ignored: $ignored_path"
  fi
  pass "ignored path remains excluded: $ignored_path"
done

echo "Curated workspace repo verification passed"
