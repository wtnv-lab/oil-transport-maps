#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if "$repo_dir/build.sh" all; then
  open "$repo_dir/dist"
else
  printf '\n作図に失敗しました。上のメッセージと README.md を確認してください。\n'
  read -r reply
  exit 1
fi
