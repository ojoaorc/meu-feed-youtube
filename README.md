# Meu feed do YouTube (sem algoritmo)

Página estática com os vídeos mais recentes de uma lista fixa de canais, em ordem cronológica, sem recomendações.
Atualizada a cada 3 horas pelo GitHub Actions e publicada no GitHub Pages.

## Como funciona
- `channels.json` — a lista de canais (nome, handle, `channel_id`).
- `build.py` — lê o feed RSS público de cada canal (`youtube.com/feeds/videos.xml?channel_id=...`), junta tudo e gera `docs/index.html` + `docs/feed.json`. Só biblioteca padrão do Python; não precisa de chave de API.
- `template.html` — a página. Busca, filtros por canal e período, player embutido, marcar como visto e selo "NOVO" desde a última visita (tudo no `localStorage` do navegador).
- Painel **Canais** (ícone no topo): adiciona/remove canais editando `channels.json` no repositório pela API do GitHub. Precisa de um token fine-grained com `Contents: Read and write` só neste repositório, salvo apenas no navegador.
- Player embutido usa `youtube.com/embed`, então vale o login do YouTube do próprio navegador (Premium sem anúncios). Safari bloqueia cookies de terceiros por padrão; no Chrome funciona.
- `.github/workflows/build.yml` — roda o script e publica no Pages.

## Adicionar um canal
Pelo painel Canais na própria página, ou editando `channels.json`: basta `{"handle": "nomedocanal"}`; o `build.py` resolve ID, nome e avatar.

## Rodar local
```bash
python3 build.py && open docs/index.html
```

## Limitações
- O RSS do YouTube traz só os ~15 vídeos mais recentes de cada canal e inclui Shorts.
- Contagem de views vem do RSS e pode estar defasada.
