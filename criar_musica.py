import json
import re
import sys
import time
import unicodedata
from pathlib import Path

from deep_translator import GoogleTranslator
from utilidades import dividir_linha_em_palavras, normalizar_chave_de_palavra

PASTA_MUSICAS = Path(__file__).parent / "musicas"

PADRAO_TIMESTAMP = re.compile(r"\[(\d{2}):(\d{2})[.:](\d{2,3})\]")


def transformar_em_nome_de_pasta(titulo: str, artista: str = "") -> str:
    if artista:
        titulo_limpo = "".join(c for c in titulo if c not in r'<>:"/\|?*')
        artista_limpo = "".join(c for c in artista if c not in r'<>:"/\|?*')
        return f"{artista_limpo} - {titulo_limpo}"

    texto_sem_acentos = unicodedata.normalize("NFKD", titulo)
    texto_sem_acentos = texto_sem_acentos.encode("ascii", "ignore").decode("ascii")
    texto_minusculo = texto_sem_acentos.lower()
    texto_limpo = re.sub(r"[^a-z0-9]+", "-", texto_minusculo).strip("-")
    return texto_limpo or "musica-sem-nome"


def analisar_texto_lrc(texto_lrc: str) -> list[dict]:
    linhas_extraidas = []

    for linha_bruta in texto_lrc.splitlines():
        correspondencia = PADRAO_TIMESTAMP.search(linha_bruta)
        if not correspondencia:
            continue

        minutos, segundos, centesimos = correspondencia.groups()
        centesimos_normalizados = centesimos.ljust(3, "0")[:3]
        tempo_em_segundos = (
            int(minutos) * 60 + int(segundos) + int(centesimos_normalizados) / 1000
        )

        texto_da_linha = PADRAO_TIMESTAMP.sub("", linha_bruta).strip()
        if texto_da_linha:
            linhas_extraidas.append({"tempo": round(tempo_em_segundos, 2), "fr": texto_da_linha})

    linhas_extraidas.sort(key=lambda linha: linha["tempo"])
    return linhas_extraidas


def ler_linhas_do_lrc(caminho_do_lrc: Path) -> list[dict]:
    with open(caminho_do_lrc, encoding="utf-8") as arquivo:
        return analisar_texto_lrc(arquivo.read())


def tentar_traduzir(texto, idioma_destino):
    if not texto or not texto.strip():
        return ""
    try:
        time.sleep(0.5)
        return GoogleTranslator(source="fr", target=idioma_destino).translate(texto)
    except Exception as e:
        print(f"Erro ao traduzir: {e}")
        return ""


def montar_vocabulario(linhas: list[dict], traduzir_automaticamente: bool) -> dict:
    vocabulario = {}

    for linha in linhas:
        for palavra_bruta in dividir_linha_em_palavras(linha["fr"]):
            chave = normalizar_chave_de_palavra(palavra_bruta)
            if not chave or chave in vocabulario or chave.isdigit():
                continue

            if traduzir_automaticamente:
                vocabulario[chave] = {
                    "pt": tentar_traduzir(chave, "pt"),
                    "en": tentar_traduzir(chave, "en"),
                }
            else:
                vocabulario[chave] = {"pt": "", "en": ""}

    return vocabulario


def criar_arquivo_da_musica(caminho_do_lrc: str, titulo: str, artista: str, traduzir_automaticamente: bool):
    linhas = ler_linhas_do_lrc(Path(caminho_do_lrc))

    if not linhas:
        print("Nenhuma linha com timestamp foi encontrada nesse .lrc. Confira o arquivo.")
        return

    for linha in linhas:
        if traduzir_automaticamente:
            linha["pt"] = tentar_traduzir(linha["fr"], "pt")
            linha["en"] = tentar_traduzir(linha["fr"], "en")
        else:
            linha["pt"] = ""
            linha["en"] = ""

    vocabulario = montar_vocabulario(linhas, traduzir_automaticamente)

    dados_da_musica = {
        "titulo": titulo,
        "artista": artista,
        "arquivo_audio": "audio.mp3",
        "linhas": linhas,
        "vocabulario": vocabulario,
    }

    nome_da_pasta = transformar_em_nome_de_pasta(titulo, artista)
    pasta_da_musica = PASTA_MUSICAS / nome_da_pasta
    pasta_da_musica.mkdir(parents=True, exist_ok=True)

    caminho_do_json = pasta_da_musica / "letra.json"
    with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
        json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)

    print(f"Música criada em: {pasta_da_musica}")
    print(f"-> Agora coloque o arquivo de áudio em: {pasta_da_musica / 'audio.mp3'}")
    if traduzir_automaticamente:
        print("-> As traduções foram preenchidas automaticamente.")
    else:
        print("-> Preencha os campos 'pt' e 'en' de cada linha manualmente no letra.json.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python criar_musica.py <caminho_lrc> <titulo> <artista> [--sem-traducao]")
        sys.exit(1)

    caminho_lrc_informado = sys.argv[1]
    titulo_informado = sys.argv[2]
    artista_informado = sys.argv[3]
    usar_traducao_automatica = "--sem-traducao" not in sys.argv

    criar_arquivo_da_musica(caminho_lrc_informado, titulo_informado, artista_informado, usar_traducao_automatica)