#!/usr/bin/env python3
"""Mostra o IP da TV, se o MAC já estiver no cache de vizinhos do Linux."""

import json
import os
import re
import subprocess
import sys


def main():
    mac = os.environ.get("PEREBAS_TV_MAC", "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{2}(?::[0-9a-f]{2}){5}", mac):
        print("Defina PEREBAS_TV_MAC no formato aa:bb:cc:dd:ee:ff.", file=sys.stderr)
        return 2
    try:
        rows = json.loads(subprocess.check_output(["ip", "-j", "neigh", "show"], text=True))
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print("Falha ao ler os vizinhos de rede: " + str(error), file=sys.stderr)
        return 1
    matches = [row for row in rows if row.get("lladdr", "").lower() == mac]
    if not matches:
        print("TV não encontrada no cache local de vizinhos. O MAC não revela o IP sozinho;")
        print("a TV precisa ter trocado tráfego com o PC na mesma rede local.")
        return 1
    for row in matches:
        print("TV: %s  interface: %s  estado: %s" %
              (row.get("dst", "?"), row.get("dev", "?"), ",".join(row.get("state", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
