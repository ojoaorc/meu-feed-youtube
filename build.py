#!/usr/bin/env python3
"""Lê channels.json, busca o feed RSS de cada canal do YouTube e gera docs/index.html + docs/feed.json.

Usa o feed RSS público do YouTube (sem chave de API, sem cota):
https://www.youtube.com/feeds/videos.xml?channel_id=UC...
Cada feed traz os ~15 vídeos mais recentes do canal.

O endpoint de RSS às vezes passa alguns minutos respondendo 404 para todo mundo. Por isso cada canal
tem três caminhos, tentados em ordem: RSS por channel_id, RSS pela playlist de uploads (UU...) e, se os
dois falharem, a página pública /videos do canal (vídeos novos ganham data exata pela página do vídeo).
Canais que ainda assim falharem são tentados de novo depois de uma pausa.

Entradas de channels.json podem ter só "handle" (ex.: "garyseconomics"); o channel_id,
o nome e o avatar são resolvidos aqui a partir da página pública do canal.
"""
import base64, hashlib, html as _html, json, os, re, shutil, sys, time, urllib.error, urllib.request, xml.etree.ElementTree as ET
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


def fetch(url, tries=6):
    """GET com novas tentativas. O RSS do YouTube às vezes responde 404/500 de forma intermitente."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1) if not isinstance(e, urllib.error.HTTPError) or e.code >= 500 or e.code == 404 else 1)


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
        m = re.search(r'"externalId":"(UC[\w-]{22})"', html)
        if m:
            ch["channel_id"] = m.group(1)
    elif not re.fullmatch(r"UC[\w-]{22}", cid):
        ch["channel_id"] = None
        ch["resolve_error"] = "channel_id inválido"
    m = re.search(r'<meta property="og:image" content="(https://yt3\.(?:googleusercontent|ggpht)\.com/[^"]+)"', html)
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


def _channel_videos(o):
    """Percorre o JSON da página do canal e devolve (videoId, título) de cada vídeo listado.
    Aceita o layout antigo (videoRenderer) e o atual (lockupViewModel)."""
    if isinstance(o, dict):
        r = o.get("videoRenderer")
        if isinstance(r, dict) and r.get("videoId"):
            yield r["videoId"], "".join(x.get("text", "") for x in r.get("title", {}).get("runs", []))
        lv = o.get("lockupViewModel")
        if isinstance(lv, dict) and lv.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO" and lv.get("contentId"):
            yield lv["contentId"], lv.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}).get("content", "")
        for v in o.values():
            yield from _channel_videos(v)
    elif isinstance(o, list):
        for v in o:
            yield from _channel_videos(v)


def _watch_details(vid):
    """Data exata, título e descrição de um vídeo, lidos da página /watch (só para vídeos ainda desconhecidos)."""
    html = fetch(f"https://www.youtube.com/watch?v={vid}", tries=2).decode("utf-8", "replace")
    m = re.search(r'"publishDate":"([^"]+)"', html) or re.search(r'itemprop="datePublished" content="([^"]+)"', html)
    if not m:
        raise ValueError("sem publishDate")
    published = datetime.fromisoformat(m.group(1)).astimezone(timezone.utc).isoformat(timespec="seconds")
    t = re.search(r'<meta name="title" content="([^"]*)"', html)
    d = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', html)
    v = re.search(r'"viewCount":"(\d+)"', html)
    return {
        "published": published,
        "title": _html.unescape(t.group(1)) if t else None,
        "description": json.loads('"' + d.group(1) + '"')[:400] if d else "",
        "views": int(v.group(1)) if v else None,
    }


def scrape_channel(ch, prev, max_new=10):
    """Plano B sem RSS: lê a página /videos do canal. Vídeos já conhecidos vêm do histórico; os novos
    buscam data exata na própria página do vídeo (no máximo max_new por rodada)."""
    html = fetch(f"https://www.youtube.com/channel/{ch['channel_id']}/videos", tries=2).decode("utf-8", "replace")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        raise ValueError("página do canal sem ytInitialData")
    out, new = [], 0
    seen = set()
    for vid, title in _channel_videos(json.loads(m.group(1))):
        if vid in seen or not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            continue
        seen.add(vid)
        if vid in prev:
            out.append(dict(prev[vid], channel=ch["name"], channel_id=ch["channel_id"]))
            continue
        if new >= max_new:
            continue
        new += 1
        det = _watch_details(vid)
        out.append({
            "id": vid,
            "title": det["title"] or title,
            "channel": ch["name"],
            "channel_id": ch["channel_id"],
            "published": det["published"],
            "url": f"https://www.youtube.com/watch?v={vid}",
            "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "description": det["description"],
            "views": det["views"],
            "is_short": False,   # a aba /videos não lista Shorts
        })
    if not out:
        raise ValueError("página do canal sem vídeos")
    return out


def collect(ch, prev):
    """Vídeos de um canal: RSS (duas URLs) e, se ambos falharem, a página do canal. Devolve (vídeos, origem)."""
    cid = ch["channel_id"]
    errs = []
    for url in (f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}",
                f"https://www.youtube.com/feeds/videos.xml?playlist_id=UU{cid[2:]}"):
        try:
            return parse(fetch(url, tries=3), ch), "rss"
        except Exception as e:  # noqa: BLE001
            errs.append(str(e))
    try:
        return scrape_channel(ch, prev), "página do canal"
    except Exception as e:  # noqa: BLE001
        errs.append(f"página: {e}")
    raise RuntimeError("; ".join(errs))


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
        vid = e.findtext("yt:videoId", namespaces=NS) or ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):   # só IDs com cara de ID entram no HTML
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
    # histórico: o que já foi publicado (o RSS só traz os ~15 últimos de cada canal) — também serve ao plano B
    prev = load_previous()
    pending = []
    for ch in raw:
        ch = resolve(ch)
        channels.append(ch)
        if not ch.get("channel_id"):
            errors.append(f"{ch.get('name') or ch.get('handle')}: não achei o channel_id")
            print(f"ERRO {ch}", file=sys.stderr)
            continue
        pending.append(ch)
    # duas passadas: quem falhar na primeira é tentado de novo depois de uma pausa, para sair da janela ruim
    for attempt in range(2):
        if attempt and pending:
            pause = 120 if os.environ.get("GITHUB_ACTIONS") else 5
            print(f"{len(pending)} canal(is) sem resposta; nova tentativa em {pause}s", file=sys.stderr)
            time.sleep(pause)
        failed = []
        for ch in pending:
            try:
                vs, origem = collect(ch, prev)
                videos += vs
                print(f"ok   {ch['name']} ({len(vs)}, via {origem})", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                failed.append((ch, e))
                print(f"ERRO {ch['name']}: {e}", file=sys.stderr)
        pending = [ch for ch, _ in failed]
    errors += [f"{ch['name']}: {e}" for ch, e in failed]
    if not videos and not prev:
        sys.exit("nenhum vídeo obtido e sem histórico; abortando para não publicar página vazia")
    if not videos:
        errors.append("YouTube não respondeu nesta rodada; mostrando o histórico")
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
    html = html.replace("__FEED_JSON__", payload)
    # CSP: só o script inline desta página (pelo hash) pode rodar; nenhum script externo, nenhum handler inline.
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    html = html.replace("__SCRIPT_HASH__", f"sha256-{digest}")
    (docs / "index.html").write_text(html)
    print(f"{len(videos)} vídeos de {len(channels)} canais ({sum(1 for v in videos if v.get("is_short"))} Shorts) -> docs/index.html", file=sys.stderr)


if __name__ == "__main__":
    main()
