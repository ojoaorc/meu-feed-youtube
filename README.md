# Meu feed do YouTube (sem algoritmo)

Página estática com os vídeos mais recentes de uma lista fixa de canais, em ordem cronológica, sem recomendações.
Atualizada a cada 3 horas pelo GitHub Actions e publicada no GitHub Pages.

## Como funciona
- `channels.json` — a lista de canais (nome, handle, `channel_id`).
- `build.py` — lê o feed RSS público de cada canal (`youtube.com/feeds/videos.xml?channel_id=...`), junta tudo e gera `docs/index.html` + `docs/feed.json`. Só biblioteca padrão do Python; não precisa de chave de API.
- `template.html` — a página. Filtros por canal e período, marcar como visto e selo "NOVO" desde a última visita ficam no `localStorage` do navegador.
- `.github/workflows/build.yml` — roda o script e publica no Pages.

## Adicionar um canal
1. Abra `https://www.youtube.com/@handle` e procure `channel_id=UC...` no código-fonte (ou use `curl -sL URL | grep -oE 'channel_id=UC[^"&]+'`).
2. Acrescente uma linha em `channels.json` e faça push. O workflow republica a página.

## Rodar local
```bash
python3 build.py && open docs/index.html
```

## Limitações
- O RSS do YouTube traz só os ~15 vídeos mais recentes de cada canal e inclui Shorts.
- Contagem de views vem do RSS e pode estar defasada.
