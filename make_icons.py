#!/usr/bin/env python3
"""Gera os ícones PNG do PWA (quadrado vermelho arredondado com triângulo de play). Só biblioteca padrão."""
import struct, zlib
from pathlib import Path

def png(size, path):
    r = size * 0.22  # raio dos cantos
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            # canto arredondado
            cx = min(max(x, r), size - 1 - r); cy = min(max(y, r), size - 1 - r)
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            if not inside:
                row += b"\x00\x00\x00\x00"; continue
            # triângulo de play: vértices (0.38,0.28) (0.38,0.72) (0.74,0.5)
            px, py = x / size, y / size
            tri = 0.38 <= px <= 0.74 and abs(py - 0.5) <= (0.74 - px) / (0.74 - 0.38) * 0.22
            row += b"\xff\xff\xff\xff" if tri else b"\xe6\x39\x46\xff"
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)

for s, name in [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]:
    png(s, Path(__file__).parent / "static" / name)
    print("ok", name)
