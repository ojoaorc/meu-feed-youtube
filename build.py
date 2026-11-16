#!/usr/bin/env python3
"""Lê channels.json, busca o feed RSS de cada canal do YouTube e gera docs/index.html + docs/feed.json.

Usa o feed RSS público do YouTube (sem chave de API, sem cota):
https://www.youtube.com/feeds/videos.xml?channel_id=UC...
Cada feed traz os ~15 vídeos mais recentes do canal.

Entradas de channels.json podem ter só "handle" (ex.: "garyseconomics"); o channel_id,
o nome e o avatar são resolvidos aqui a partir da página pública do canal.
"""
import json, os, re, shutil, sys, time, urllib.error, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
REPO = os.environ.get("GITHUB_REPOSITORY", "ojoaorc/meu-feed-youtube")
OWNER, NAME = REPO.split("/")
LIVE_FEED = f"https://{OWNER}.github.io/{NAME}/feed.json"   # histórico já publicado
MAX_DAYS = 730          # guarda até 2 anos de histórico
MAX_VIDEOS = 3000
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def is_short(vid):
    """True se /shorts/ID responde 200; vídeo normal redireciona (303) para /watch. None se não deu para saber."""
    req = urllib.request.Request(f"https://www.youtube.com/shorts/{vid}", method="HEAD", headers={"User-Agent": UA})
    for i in range(2):
        try:
            with _opener.open(req, timeout=15) as r:
                return r.status == 200
        except urllib.error.HTTPError as e:
            if 300 <= e.code < 400:
                return False
        except Exception:  # noqa: BLE001
            time.sleep(1)
    return None


def load_previous():
    """Vídeos já conhecidos: do feed publicado no Pages e, se existir, do docs/feed.json local."""
    prev = {}
    for src in (LIVE_FEED, ROOT / "docs" / "feed.json"):
        try:
            data = json.loads(fetch(src) if isinstance(src, str) else src.read_text())
            for v in data.get("videos", []):
                prev.setdefault(v["id"], v)
            print(f"histórico: {len(data.get('videos', []))} vídeos de {src}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"sem histórico em {src}: {e}", file=sys.stderr)
    return prev


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

    # ---- histórico: junta com o que já foi publicado (o RSS só traz os ~15 últimos de cada canal)
    prev = load_previous()
    active_ids = {c["channel_id"] for c in channels if c.get("channel_id")}
    merged = {v["id"]: v for v in videos}
    for vid, old in prev.items():
        if vid not in merged and old.get("channel_id") in active_ids:
            merged[vid] = old
        elif vid in merged:
            for k in ("is_short", "first_seen"):
                if k in old and old[k] is not None:
                    merged[vid].setdefault(k, old[k])
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cutoff = (datetime.now(timezone.utc).timestamp() - MAX_DAYS * 86400)
    videos = [v for v in merged.values()
              if datetime.fromisoformat(v["published"]).timestamp() >= cutoff]
    for v in videos:
        v.setdefault("first_seen", now_iso)

    # ---- Shorts: só consulta os vídeos ainda não classificados
    pending = [v for v in videos if v.get("is_short") is None]
    if pending:
        with ThreadPoolExecutor(max_workers=4) as ex:
            for v, flag in zip(pending, ex.map(lambda v: is_short(v["id"]), pending)):
                v["is_short"] = flag
        print(f"shorts: {len(pending)} classificados, {sum(1 for v in pending if v['is_short'])} são Shorts", file=sys.stderr)

    videos.sort(key=lambda v: v["published"], reverse=True)
    videos = videos[:MAX_VIDEOS]
    feed = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": REPO,
        "channels": channels,
        "errors": errors,
        "videos": videos,
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    for f in (ROOT / "static").iterdir():
        shutil.copy(f, docs / f.name)
    (docs / "feed.json").write_text(json.dumps(feed, ensure_ascii=False, indent=1))
    html = (ROOT / "template.html").read_text()
    payload = json.dumps(feed, ensure_ascii=False).replace("</", "<\\/")  # protege o </script>
    (docs / "index.html").write_text(html.replace("__FEED_JSON__", payload))
    print(f"{len(videos)} vídeos de {len(channels)} canais ({sum(1 for v in videos if v.get("is_short"))} Shorts) -> docs/index.html", file=sys.stderr)


if __name__ == "__main__":
    main()
