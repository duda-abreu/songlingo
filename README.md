# songlingo

App pessoal pra aprender francês cantando. A ideia é simples: você escolhe uma música, ela toca, a letra vai passando sincronizada com o áudio, e quando bate a curiosidade você clica na frase e vê a tradução em português e inglês na hora. Tem também um modo de estudo, onde cada palavra da letra vira uma pergunta — você tenta traduzir, o app confere e vai guardando o que você já sabe.

## como rodar

Precisa de Python 3.11+ e do [spotdl](https://github.com/spotDL/spotify-downloader) instalado se você quiser baixar músicas direto pelo app (`pip install spotdl`).

```bash
pip install -r requirements.txt
python main.py
```

Isso abre a janela do app. **Importante:** rode com `python main.py`.

## os dois modos

**ouvir** — a barra lateral lista as músicas que já estão em `musicas/`. Clica numa, dá play, e a linha que está tocando fica destacada. Clicar em qualquer linha da letra pula o áudio pra aquele trecho e mostra a tradução no painel de baixo. Tem um switch pra decidir se quer que a tradução acompanhe sozinha enquanto toca, ou só apareça quando você clicar manualmente.

**estudar palavras** — cada palavra da letra vira um botão. Clica, digita o que acha que significa, o app confere (ignora acento e maiúscula/minúscula, então "coração" e "coracao" contam igual). Se a palavra ainda não tem tradução cadastrada pra ela, o que você digitar vira a resposta oficial dali pra frente — assim o vocabulário de cada música vai crescendo com o uso.

## adicionando música

Jeito mais fácil: cola o link de uma música, álbum ou playlist do Spotify na caixa "baixar música" na barra lateral. Ele baixa o áudio via spotdl, busca a letra sincronizada sozinho (usa a API do lrclib.net) e já traduz tudo na hora. Se não encontrar letra pra alguma faixa, ela nem entra na lista — sem letra sincronizada o app não tem o que mostrar.

Pra buscar letra em lote sem passar pelo app, tem uns scripts separados:

- `gerar_letras.py` — varre `musicas/` inteira e busca letra pra qualquer pasta que ainda não tenha `letra.json`.
- `criar_musica.py` — se você já tem um arquivo `.lrc` na mão, monta a pasta e o `letra.json` a partir dele.

Todos aceitam `--sem-traducao` se você preferir preencher pt/en na mão em vez de usar tradução automática.

## sobre as traduções

A tradução automática usa o Google Translate por baixo (via `deep-translator`), que não tem API oficial gratuita — então cada palavra e cada linha vira uma requisição separada com uma pausa no meio pra não ser bloqueado. Pra uma música de 3 minutos com umas 100 palavras diferentes, isso demora. Baixando pelo app isso já acontece sozinho; pra traduzir o que ainda ficou pendente em `musicas/` (por exemplo, músicas adicionadas na mão), roda:

```bash
python traduzir_musicas.py
```

Ele só preenche o que ainda está vazio (então dá pra rodar de novo se cair no meio, sem perder o que já foi feito) e vai salvando linha por linha, música por música.

## estrutura

```
main.py                        # o app em si (interface, player, quiz)
utilidades.py                  # funções compartilhadas (carregar músicas, achar linha atual, busca de letra, etc)
gerar_letras.py                # varre musicas/ e busca letra pro que falta
criar_musica.py                # monta letra.json a partir de um .lrc
traduzir_musicas.py            # preenche traduções que ainda estão vazias
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

Letra e tradução vêm de fontes abertas (lrclib.net, tradução própria). O áudio baixado é só pra uso pessoal — não faz parte deste repositório nem deveria ser publicado em lugar nenhum público.
