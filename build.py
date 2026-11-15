#!/usr/bin/env python3
"""Lê channels.json, busca o feed RSS de cada canal do YouTube e gera docs/index.html.

Usa o feed RSS público do YouTube (sem chave de API, sem cota):
https://www.youtube.com/feeds/videos.xml?channel_id=UC...
Cada feed traz os ~15 vídeos mais recentes do canal.
"""
import json, sys, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "meu-feed-youtube/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def parse(xml_bytes, channel):
    root = ET.fromstring(xml_bytes)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        pub = e.findtext("a:published", namespaces=NS)
        desc = e.findtext("media:group/media:description", namespaces=NS) or ""
        views = e.find("media:group/media:community/media:statistics", NS)
        out.append({
            "id": vid,
            "title": e.findtext("a:title", namespaces=NS) or "",
            "channel": channel["name"],
            "channel_id": channel["channel_id"],
            "published": pub,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
            "description": desc[:300],
            "views": int(views.get("views", 0)) if views is not None else None,
        })
    return out


def main():
    channels = json.loads((ROOT / "channels.json").read_text())
    videos, errors = [], []
    for ch in channels:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
        try:
            videos += parse(fetch(url), ch)
            print(f"ok   {ch['name']}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{ch['name']}: {e}")
            print(f"ERRO {ch['name']}: {e}", file=sys.stderr)
    if not videos:
        sys.exit("nenhum vídeo obtido; abortando para não publicar página vazia")

    videos.sort(key=lambda v: v["published"], reverse=True)
    feed = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "channels": channels,
        "errors": errors,
        "videos": videos,
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1))
    html = (ROOT / "template.html").read_text()
    # </script> dentro do JSON quebraria a página; escapa a barra.
    payload = json.dumps(feed, ensure_ascii=False).replace("</", "<\\/")
    (docs / "index.html").write_text(html.replace("__FEED_JSON__", payload))
    print(f"{len(videos)} vídeos de {len(channels)} canais -> docs/index.html", file=sys.stderr)


if __name__ == "__main__":
    main()
