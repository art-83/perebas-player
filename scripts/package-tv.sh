#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$project_dir/build"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
cp "$project_dir/tv/"{config.xml,widget.info,index.html,settings.js,player.js} "$tmp_dir/"
if [[ -n "${PEREBAS_PC_IP:-}" ]]; then
  if [[ ! "$PEREBAS_PC_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
    echo "PEREBAS_PC_IP deve ser um IPv4" >&2
    exit 2
  fi
  sed -i "s/192\.168\.1\.10/$PEREBAS_PC_IP/" "$tmp_dir/settings.js"
fi
rm -f "$project_dir/build/PerebasPlayer.zip"
(cd "$tmp_dir" && zip -q "$project_dir/build/PerebasPlayer.zip" config.xml widget.info index.html settings.js player.js)
echo "Criado build/PerebasPlayer.zip"
