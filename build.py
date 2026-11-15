#!/usr/bin/env python3
"""Lê channels.json, busca o feed RSS de cada canal do YouTube e gera docs/index.html + docs/feed.json.

Usa o feed RSS público do YouTube (sem chave de API, sem cota):
https://www.youtube.com/feeds/videos.xml?channel_id=UC...
Cada feed traz os ~15 vídeos mais recentes do canal.

Entradas de channels.json podem ter só "handle" (ex.: "garyseconomics"); o channel_id,
o nome e o avatar são resolvidos aqui a partir da página pública do canal.
"""
import json, os, re, sys, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
REPO = os.environ.get("GITHUB_REPOSITORY", "ojoaorc/meu-feed-youtube")
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def resolve(ch):
    """Preenche channel_id, name e avatar a partir da página do canal."""
    ch = dict(ch)
    handle = (ch.get("handle") or "").lstrip("@")
    cid = ch.get("channel_id")
    url = f"https://www.youtube.com/channel/{cid}" if cid else f"https://www.youtube.com/@{handle}"
    try:
        html = fetch(url).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        ch.setdefault("name", handle or cid)
        ch["resolve_error"] = str(e)
        return ch
    if not cid:
        m = re.search(r'"externalId":"(UC[\w-]+)"', html)
        if m:
            ch["channel_id"] = m.group(1)
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m:
        ch["avatar"] = m.group(1).replace("&amp;", "&")
    if not ch.get("name"):
        m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        ch["name"] = (m.group(1) if m else handle).replace("&#39;", "'").replace("&amp;", "&")
    if not handle:
        m = re.search(r'"canonicalBaseUrl":"/@([^"]+)"', html)
        if m:
            ch["handle"] = m.group(1)
    return ch


def parse(xml_bytes, channel):
    root = ET.fromstring(xml_bytes)
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        desc = e.findtext("media:group/media:description", namespaces=NS) or ""
        views = e.find("media:group/media:community/media:statistics", NS)
        out.append({
            "id": vid,
            "title": e.findtext("a:title", namespaces=NS) or "",
            "channel": channel["name"],
            "channel_id": channel["channel_id"],
            "published": e.findtext("a:published", namespaces=NS),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "description": desc[:400],
            "views": int(views.get("views", 0)) if views is not None else None,
        })
    return out


def main():
    raw = json.loads((ROOT / "channels.json").read_text())
    channels, videos, errors = [], [], []
    for ch in raw:
        ch = resolve(ch)
        channels.append(ch)
        if not ch.get("channel_id"):
            errors.append(f"{ch.get('name') or ch.get('handle')}: não achei o channel_id")
            print(f"ERRO {ch}", file=sys.stderr)
            continue
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['channel_id']}"
        try:
            vs = parse(fetch(url), ch)
            videos += vs
            print(f"ok   {ch['name']} ({len(vs)})", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{ch['name']}: {e}")
            print(f"ERRO {ch['name']}: {e}", file=sys.stderr)
    if not videos:
        sys.exit("nenhum vídeo obtido; abortando para não publicar página vazia")

    videos.sort(key=lambda v: v["published"], reverse=True)
    feed = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": REPO,
        "channels": channels,
        "errors": errors,
        "videos": videos,
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1))
    html = (ROOT / "template.html").read_text()
    payload = json.dumps(feed, ensure_ascii=False).replace("</", "<\\/")  # protege o </script>
    (docs / "index.html").write_text(html.replace("__FEED_JSON__", payload))
    print(f"{len(videos)} vídeos de {len(channels)} canais -> docs/index.html", file=sys.stderr)


if __name__ == "__main__":
    main()
