#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../tv"
mkdir -p ../build
zip -q -j ../build/PerebasPlayer.zip config.xml widget.info index.html settings.js player.js
echo "Criado build/PerebasPlayer.zip"
