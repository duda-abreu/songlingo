# frenchlingo

App pessoal pra aprender francês cantando. Você ouve com letra sincronizada, consulta traduções, pratica vocabulário e treina compreensão oral com ditados de trechos reais das músicas. Tem também um curso à parte, o parcours défi, com lições de gramática, vocabulário e conversação — incluindo frases prontas pra viagem.

## como rodar

Precisa de Python 3.11+ e do [spotdl](https://github.com/spotDL/spotify-downloader) instalado se você quiser baixar músicas direto pelo app (`python -m pip install spotdl`).

```bash
python -m pip install -r requirements.txt
python main.py
```

No Windows, também dá para instalar com:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

Os dois métodos chamam o `pip` do próprio Python e não exigem conta no Safety.

## modos de estudo

**ouvir** — a barra lateral lista as músicas que já estão em `musicas/`. Clica, dá play, e a linha que está tocando fica destacada. Clicar em qualquer linha da letra pula o áudio pra aquele trecho e mostra a tradução no painel de baixo. Tem um switch pra decidir se quer que a tradução acompanhe sozinha enquanto toca, ou só apareça quando você clicar manualmente.

**estudar palavras** — cada palavra da letra vira um botão. Clica, digita o que acha que significa, o app confere (ignora acento e maiúscula/minúscula, então "coração" e "coracao" contam igual). Se a palavra ainda não tem tradução cadastrada pra ela, o que você digitar vira a resposta oficial dali pra frente — assim o vocabulário de cada música vai crescendo com o uso.

**ditado** — o app sorteia uma frase em francês, toca só aquele trecho e espera você escrever o que ouviu. A correção tolera acentos, pontuação e pequenos erros, mostra palavras que faltaram ou sobraram e permite repetir, revelar ou pular sem marcar erro.

**inglês → francês** — mostra uma frase em inglês, tirada das traduções das músicas ou do banco de prática, e pede a versão em francês. A correção aceita respostas quase certas (mostra "quase lá" quando falta pouco) e ignora acentos, pontuação e contrações.

**palavras aprendidas** — reúne o vocabulário já acertado para busca e revisão, junto com os pontos fracos: frases e palavras em que você errou, pra rever depois.

**parcours défi** — curso à parte, separado das músicas, acessível pelo card na barra lateral. Tem 13 unidades e mais de 200 atividades de compreensão, escuta, escrita, tradução, associação e produção, organizadas por nível (A2.1, A2.2, passerelle B1) e uma seção extra de conversação pra viagem — pedir informação na rua, pedir comida num restaurante, perguntar as horas, conversar num hotel.

## adicionando música

Cola o link de uma música, álbum ou playlist do Spotify na caixa "baixar música" na barra lateral. Ele baixa o áudio via spotdl, busca a letra sincronizada sozinho (usa a API do lrclib.net) e já traduz tudo na hora. Se não encontrar letra pra alguma faixa, ela nem entra na lista — sem letra sincronizada o app não tem o que mostrar.

Pra buscar letra em lote sem passar pelo app, tem uns scripts separados:

- `gerar_letras.py` — varre `musicas/` inteira e busca letra pra qualquer pasta que ainda não tenha `letra.json`.
- `criar_musica.py` — se você já tem um arquivo `.lrc` na mão, monta a pasta e o `letra.json` a partir dele.

Todos aceitam `--sem-traducao` se você preferir preencher pt/en na mão em vez de usar tradução automática.

## sobre as traduções

A tradução automática usa o Google Translate (via `deep-translator`), que não tem API oficial gratuita — então cada palavra e cada linha vira uma requisição separada com uma pausa no meio pra não ser bloqueado. Pra uma música de 3 minutos com umas 100 palavras diferentes, isso demora. Baixando pelo app isso já acontece sozinho; pra traduzir o que ainda ficou pendente em `musicas/` (por exemplo, músicas adicionadas na mão), roda:

```bash
python traduzir_musicas.py
```

Ele só preenche o que ainda está vazio (então dá pra rodar de novo se cair no meio, sem perder o que já foi feito) e vai salvando linha por linha, música por música.

## versão web

Tem uma versão bem mais simples rodando direto no navegador, em `docs/` — dá pra publicar como GitHub Pages. Ela mostra a letra sincronizada, a tradução e o modo de estudo, mas não guarda nem baixa áudio nenhum: você escolhe o mp3 do seu computador toda vez que for ouvir, ele nunca sai da sua máquina.

Se você quiser só o parcours défi, sem nada de música, `docs/defi-standalone.html` é uma página separada só com o curso — é nela que o `estudar.bat` abre direto (duplo clique nele pra estudar sem precisar mexer em nada).

Pra atualizar os dados que a versão web usa (depois de adicionar música nova ou mudar uma unidade do défi):

```bash
python curso_defi.py
```

Isso lê `defi_data.json` e `defi_pratica.json`, junta tudo e gera `docs/defi-data.js`. Pra atualizar a lista de músicas do site, roda também:

```bash
python gerar_site.py
```

Pra publicar: nas configurações do repositório no GitHub, em Pages, escolhe a branch `main` e a pasta `/docs` como fonte.

## testes

```bash
python -m unittest discover
```

Cobre a lógica do défi, do modo estudo (correção de ditado e tradução) e o carregamento das músicas.

## estrutura

```
main.py                        # o app em si (interface, player, quiz)
utilidades.py                  # funções compartilhadas (carregar músicas, achar linha atual, busca de letra, etc)
estudo.py                      # correção de ditado e tradução inglês → francês
gerar_letras.py                # varre musicas/ e busca letra pro que falta
criar_musica.py                # monta letra.json a partir de um .lrc
traduzir_musicas.py            # preenche traduções que ainda estão vazias
defi_desktop.py                # painel do parcours défi no app desktop
defi_data.json                 # unidades principais do parcours défi
defi_pratica.json              # atividades extras de cada unidade do défi
curso_defi.py                  # junta defi_data.json + defi_pratica.json e gera docs/defi-data.js
gerar_site.py                  # gera os dados que a versão web usa (músicas)
docs/                          # versão web (HTML/CSS/JS puro, sem áudio)
docs/defi-standalone.html      # só o parcours défi, sem nada de música
estudar.bat                    # abre o parcours défi direto, sem precisar rodar nada na mão
test_*.py                      # testes automatizados
musicas/
  nome-da-musica/
    audio.mp3
    letra.json
```

Cada `letra.json` tem esse formato:

```json
{
  "titulo": "Nome da Música",
  "artista": "Nome do Artista",
  "arquivo_audio": "audio.mp3",
  "linhas": [
    {"tempo": 4.5, "fr": "frase em francês", "pt": "tradução", "en": "translation"}
  ],
  "vocabulario": {
    "palavra": {"pt": "tradução", "en": "translation"}
  }
}
```

`tempo` é em segundos, é o instante em que a linha começa a tocar.

## direitos autorais

Letra e tradução vêm de fontes abertas (lrclib.net, tradução própria). O áudio baixado é só pra uso pessoal — não faz parte deste repositório e não pode ser publicado em lugar público. O conteúdo do parcours défi é autoral, inspirado na abordagem acional do FLE; não reproduz nenhum livro didático.
