# Manual de operação

Como cuidar deste feed sem ajuda de ninguém. Tudo é feito pelo site do GitHub, no navegador; não precisa de terminal nem de programa instalado. Onde houver atalho de terminal, ele aparece como opção, nunca como obrigação.

Endereços:

- Página do feed: https://ojoaorc.github.io/meu-feed-youtube/
- Repositório (código): https://github.com/ojoaorc/meu-feed-youtube

---

## 1. Como a coisa funciona, em uma figura

```
channels.json  ──►  build.py  ──►  docs/index.html  ──►  GitHub Pages (a página que você abre)
 (lista de             (roda no           (página pronta,
  canais)               GitHub a           com os vídeos
                        cada 3 h)          embutidos)
```

1. `channels.json` é a lista de canais. É o único arquivo que você precisa mexer no dia a dia.
2. A cada 3 horas o GitHub roda `build.py`. Ele lê o feed RSS público de cada canal (o YouTube publica um por canal, sem precisar de chave ou login), junta os vídeos, ordena por data e gera a página. Se o RSS não responder, lê a página pública do canal como plano B.
   - O RSS só traz os 15 vídeos mais recentes de cada canal. Para não perder os anteriores, o script baixa o `feed.json` que já está publicado e junta com o novo. Assim o histórico cresce a cada rodada (até 2 anos ou 3.000 vídeos).
   - Para cada vídeo novo ele pergunta ao YouTube se é um Short (um pedido leve por vídeo, só na primeira vez que o vídeo aparece). Na página, o botão **Sem Shorts / Com Shorts** usa essa marcação.
3. A página gerada vai para o GitHub Pages. Nada roda no seu computador.

O que fica no seu navegador, e não no GitHub: quais vídeos você marcou como vistos, quais canais estão ligados no filtro, se Shorts aparecem, o tema claro ou escuro e a data da sua última visita (que dá o selo NOVO). Isso é por navegador: o celular não sabe o que você marcou no Mac.

---

## 1a. Atalhos da página

- **Novos**: chip que aparece quando há vídeos publicados desde a sua última visita; clique para ver só eles.
- Clique num canal para ver só os vídeos dele; **Todos a bordo** reúne todos novamente. Tudo isso fica salvo no navegador, inclusive o período escolhido.
- **Abrir: aqui / no YouTube**: escolhe se a capa e o título abrem o player embutido ou o app/site do YouTube (com seu login e Premium). No iPhone/iPad o padrão é "no YouTube", porque o player embutido roda deslogado lá (veja a seção 6).
- **Player**: capa ou título abrem o vídeo na própria página. Setas ← → (ou os botões) passam para o anterior/próximo da lista visível. Fechar encerra a reprodução e devolve o foco ao vídeo. O botão Voltar do celular fecha o player.
- Teclado: `/` foca a busca, `Esc` fecha o player ou limpa a busca.
- No celular, os filtros rolam horizontalmente e o cabeçalho acompanha a página, liberando espaço para assistir.

## 1b. Instalar como aplicativo no celular

A página é um PWA: dá para colocar na tela inicial, com ícone e tela cheia, sem barra do navegador.

- **iPhone (Safari):** abra a página, toque no botão Compartilhar (quadrado com seta) e em **Adicionar à Tela de Início**.
- **Android (Chrome):** abra a página, toque no menu ⋮ e em **Instalar app** (ou **Adicionar à tela inicial**).
- **Mac/PC (Chrome):** ícone de instalar que aparece na barra de endereço, à direita.

É só um atalho para a mesma página; nada é baixado além dela. Lembre que o player embutido depende do login do navegador que abriu o PWA.

## 2. Adicionar um canal

1. Descubra o handle do canal. É o nome que começa com `@` na página do canal no YouTube, por exemplo `youtube.com/@garyseconomics` tem o handle `garyseconomics`. Cuidado com canais homônimos: confira se é o canal certo antes de copiar.
2. Abra https://github.com/ojoaorc/meu-feed-youtube/edit/main/channels.json (precisa estar logado no GitHub).
3. Acrescente uma linha no fim da lista, antes do `]` final, seguindo o padrão. Repare na vírgula no fim da linha anterior:

   ```json
   [
     {"name": "Econoclasts", "handle": "Econoclasts", "channel_id": "UChvbiD-vtewbaXD71UCa-pA"},
     ...
     {"name": "ParkNotes", "handle": "ParkerNotes", "channel_id": "UCt1ES-_FMXQfM3JeO_FrOXw"},
     {"handle": "nomedocanal"}
   ]
   ```

   Só o `handle` basta. O script descobre sozinho o ID, o nome e o avatar. Se preferir, pode informar `channel_id` (o código que começa com `UC`) em vez do handle; serve igual.
4. Clique no botão verde **Commit changes...**, escreva uma mensagem curta (por exemplo "adiciona canal X") e confirme em **Commit changes**.
5. Espere cerca de 1 minuto. O commit dispara a atualização automática. Recarregue a página do feed e o canal aparece nos filtros do topo.

Se o canal não aparecer, veja a seção 6.

## 3. Remover um canal

1. Abra https://github.com/ojoaorc/meu-feed-youtube/edit/main/channels.json.
2. Apague a linha inteira do canal. Se era a última linha da lista, apague também a vírgula do fim da linha que ficou por último, para o arquivo continuar válido.
3. **Commit changes...** e confirme. Em cerca de 1 minuto o canal some da página.

Para esconder um canal só por um tempo, sem apagar, não precisa mexer em nada: na página, clique no nome do canal no topo para desligar o filtro dele. Duplo clique num canal mostra só ele.

## 4. Forçar uma atualização agora

A atualização automática roda a cada 3 horas. Para não esperar:

1. Abra https://github.com/ojoaorc/meu-feed-youtube/actions/workflows/build.yml.
2. Clique em **Run workflow** (botão à direita) e de novo em **Run workflow** no menu que abre.
3. Em cerca de 1 minuto a página está atualizada.

## 5. Ver se a atualização está funcionando

1. Abra https://github.com/ojoaorc/meu-feed-youtube/actions.
2. Cada linha é uma rodada. Verde com ✓ é sucesso; vermelho com ✗ é falha.
3. A própria página do feed mostra "Atualizado dd/mm hh:mm" no topo. Se essa hora estiver com mais de 3 ou 4 horas de atraso, algo parou: veja a seção 6.

## 6. Quando algo dá errado

**Um canal não aparece depois de adicionado.**
Abra a página do feed e olhe a linha "Atualizado ..." no topo. Se houver um aviso em vermelho "falhas: ...", ele diz qual canal não foi encontrado. Causas comuns: handle digitado errado (confira na URL do canal no YouTube), ou um canal que tem o nome parecido mas é outro. Corrija o `channels.json` como na seção 2.

**A linha "Atualizado ..." mostra "⚠︎ N canais sem resposta do YouTube nesta rodada".**
O YouTube às vezes passa alguns minutos respondendo "404" para o RSS de todo mundo, inclusive para a máquina do GitHub. O script tem três caminhos por canal (RSS, RSS da playlist de uploads e a página pública do canal) e, se um canal falhar em todos, espera 2 minutos e tenta de novo. Só então aparece o aviso, e mesmo assim a página continua com o histórico. Na rodada seguinte (3 horas depois) quase sempre se resolve sozinho. Se quiser, force uma rodada como na seção 4. Se o aviso persistir por um dia inteiro para o mesmo canal, o canal pode ter mudado de endereço ou sido apagado: confira no YouTube e ajuste o `channels.json`.

**A rodada ficou vermelha no Actions.**
Clique na rodada, depois em `build`, e leia a linha que começa com `ERRO`. Quase sempre é um `channels.json` com erro de digitação: vírgula faltando ou sobrando, aspas abertas sem fechar, chave `{` ou colchete `]` a mais ou a menos. Você pode colar o conteúdo do arquivo em https://jsonlint.com para apontar a linha exata. Corrija e salve de novo; a correção dispara outra rodada.

**A página mostra "nada novo" mas eu sei que saiu vídeo.**
Verifique quatro coisas: o filtro de período (talvez esteja em "2 semanas" e o vídeo é mais antigo), o filtro de canais (o canal pode estar desligado no topo), o botão "Ocultar vistos" (se estiver ativo, vídeos já marcados somem) e o botão "Sem Shorts" (o vídeo pode ser um Short). Clicar em "Tudo", "Com Shorts" e desligar "Só não vistos" mostra todos.

**Um vídeo normal está marcado como SHORT, ou um Short passou sem marca.**
A classificação vem do próprio YouTube e é feita uma vez só, quando o vídeo aparece. Raramente erra; se errar, não há o que fazer sem mexer no código (o botão "Com Shorts" mostra tudo).

**Quero zerar o histórico acumulado.**
O histórico vive no `feed.json` publicado, não no repositório. Para zerar, edite `build.py`, troque `MAX_DAYS = 730` por `MAX_DAYS = 30`, salve, espere uma rodada e volte ao valor anterior.

**O feed parou de atualizar sozinho por semanas.**
O GitHub desliga as rodadas agendadas de repositórios sem nenhum commit por 60 dias. Em https://github.com/ojoaorc/meu-feed-youtube/actions aparece um aviso com um botão para reativar. Qualquer commit (por exemplo, adicionar um canal) também reativa.

**O player embutido mostra anúncios ou pede login.**
O player usa o site do YouTube dentro da página, então vale o login do navegador em que você está. No Chrome do computador logado na sua conta Premium, toca sem anúncios. No Safari e em qualquer navegador do iPhone/iPad, o sistema bloqueia os cookies de outros sites dentro de players embutidos, e o YouTube roda deslogado; não há como mudar isso pela página. Por isso, no iPhone/iPad o padrão é o chip **Abrir: no YouTube**: tocar num vídeo abre o app do YouTube (ou o site), onde o Premium vale, e o vídeo fica marcado como visto. O chip **Abrir: aqui** volta para o player embutido, com anúncios. Alguns criadores proíbem embutir; o player avisa e o mesmo botão resolve.

**Quero limpar os "vistos" e começar do zero.**
Isso fica no navegador, não no GitHub. No navegador, apague os dados do site `ojoaorc.github.io` (em Safari: Ajustes > Privacidade > Gerenciar dados de sites; em Chrome: cadeado na barra de endereço > Cookies e dados do site > Gerenciar).

## 7. Mudar a frequência de atualização

1. Abra https://github.com/ojoaorc/meu-feed-youtube/edit/main/.github/workflows/build.yml.
2. Procure a linha `- cron: "17 */3 * * *"`. O `*/3` significa "a cada 3 horas". Troque por `*/1` para toda hora, `*/6` para a cada 6 horas, ou `"17 7 * * *"` para uma vez por dia às 7h UTC (4h em Brasília).
3. Commit changes. Não desça de 1 hora: o GitHub limita e o YouTube não publica tão rápido.

## 8. Mudar o visual ou os textos

Tudo o que aparece na página está em `template.html`. É um único arquivo com o HTML, o CSS (entre `<style>` e `</style>`) e o JavaScript (entre `<script>` e `</script>`, no fim). O que você pode mexer sem medo:

- Cores: no começo do `<style>`, o bloco `:root{ ... }` é o tema escuro e `:root[data-theme=light]{ ... }` é o claro. `--accent` é o vermelho dos botões e do selo NOVO.
- Período padrão: na linha `let rangeDays = 14, query = '';` do JavaScript, troque o 14 pelo número de dias que quiser ao abrir a página.
- Textos dos botões: são os textos dentro das tags `<button ...>...</button>` no HTML.

Depois de salvar, a rodada automática regenera a página com o novo visual. Se quebrar algo, o GitHub guarda o histórico: em https://github.com/ojoaorc/meu-feed-youtube/commits/main clique no commit anterior, abra o arquivo, use o botão de copiar e cole de volta no arquivo atual.

## 9. Testar no computador (opcional)

Só precisa do Python 3, que o Mac já tem.

```bash
git clone https://github.com/ojoaorc/meu-feed-youtube.git
cd meu-feed-youtube
python3 build.py
open docs/index.html
```

O `build.py` imprime um `ok NomeDoCanal (15)` por canal e escreve `docs/index.html`. Para mandar uma mudança feita localmente: `git add -A && git commit -m "mensagem" && git push`.

## 10. Trocar de conta, mudar o endereço ou desligar

- **Endereço:** a página fica em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`. Renomear o repositório em Settings > General muda o endereço na hora.
- **Domínio próprio:** Settings > Pages > Custom domain, seguindo o que o GitHub pede no seu provedor de DNS.
- **Desligar as atualizações sem apagar nada:** em Actions, clique em "Atualizar feed" na lateral, depois no menu `...` > Disable workflow.
- **Apagar tudo:** Settings > General > Danger Zone > Delete this repository. A página sai do ar junto.

## 11. Segurança e privacidade

O que está público e o que não está:

- O repositório é público, e precisa ser para o GitHub Pages gratuito. Nele há só código, a lista de canais e este manual. Nenhuma chave, senha ou token: o projeto não usa nenhum.
- Os commits usam o e-mail anônimo do GitHub (`83012445+ojoaorc@users.noreply.github.com`), não o seu e-mail pessoal. Para manter assim em edições pelo site do GitHub, ative em https://github.com/settings/emails as duas caixas **Keep my email addresses private** e **Block command line pushes that expose my email**. Se um dia fizer push por terminal em outra máquina, rode antes `git config user.email 83012445+ojoaorc@users.noreply.github.com` dentro da pasta do projeto.
- A página tem `noindex` (não aparece em buscadores), não usa analytics, cookies nem scripts de terceiros. O que ela guarda (vistos, filtros, tema) fica só no seu navegador.
- A página só pode carregar imagens do YouTube e o player do YouTube, e só roda o próprio script (política de segurança de conteúdo com hash). Se alguém conseguisse injetar texto malicioso via título de vídeo, ele não executaria.
- O script do GitHub Actions usa versões fixadas por hash das ações oficiais do GitHub, e o repositório só aceita ações feitas pelo próprio GitHub. Permissões do workflow: leitura do código e escrita só no Pages.
- Issues e wiki estão desligados para não virar depósito de spam.
- Ao abrir vídeos, o YouTube vê que você assistiu, como em qualquer uso logado. A página manda ao YouTube só a sua origem (`https://ojoaorc.github.io`), sem caminho nem parâmetros. O player exige isso desde 2025: sem o cabeçalho Referer ele mostra "erro 153", principalmente no Safari e no iPhone.

## 12. Mapa dos arquivos

| Arquivo | O que é | Mexer? |
|---|---|---|
| `channels.json` | Lista de canais | Sim, é o dia a dia |
| `template.html` | A página (visual e comportamento) | Só para mudar visual ou textos |
| `static/player.html` | Página intermediária que embute o player do YouTube (evita o erro 153 no iPhone) | Nunca |
| `build.py` | Script que lê o RSS, junta o histórico, marca Shorts e gera a página | Raramente |
| `static/` | Manifest e ícones do PWA; copiados para `docs/` a cada rodada | Só para trocar o ícone |
| `make_icons.py` | Gera os PNGs a partir de `static/icon.svg` no macOS (só se trocar o ícone) | Não |
| `.github/workflows/build.yml` | Agendamento e publicação no Pages | Só para mudar a frequência |
| `docs/` | Página gerada; não está no repositório (está no `.gitignore`), é produzida a cada rodada | Nunca |
| `README.md` | Resumo técnico | Não |
| `MANUAL.md` | Este manual | Quando quiser |

### Uso no iPhone

Os canais deslizam horizontalmente. Os períodos ficam visíveis; toque em **Ajustar feed** para Shorts, vistos e escolha do player. O cabeçalho acompanha a página sem encolher durante a rolagem. No player, **Fechar** fica no topo, e fechar ou usar Voltar restaura a posição da lista. Em paisagem, o painel permite rolagem interna. O login/Premium do player embutido continua dependendo das regras do navegador; **Abrir: no YouTube** permanece disponível.

No celular, o botão discreto **Topo** aparece no canto inferior após rolar a página. Ele volta aos filtros sem mudar suas escolhas e fica oculto enquanto o player está aberto.
