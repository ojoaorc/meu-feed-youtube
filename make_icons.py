#!/usr/bin/env python3
"""Gera os PNGs do PWA a partir de static/icon.svg usando o renderizador do macOS (qlmanage + sips).
Só precisa rodar quando o SVG mudar; os PNGs ficam commitados."""
import shutil, subprocess, tempfile
from pathlib import Path

static = Path(__file__).parent / "static"
svg = static / "icon.svg"
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["qlmanage", "-t", "-s", "1024", "-o", tmp, str(svg)], check=True, capture_output=True)
    big = Path(tmp) / (svg.name + ".png")
    for size, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png")]:
        out = static / name
        shutil.copy(big, out)
        subprocess.run(["sips", "-z", str(size), str(size), str(out)], check=True, capture_output=True)
        print("ok", name)
