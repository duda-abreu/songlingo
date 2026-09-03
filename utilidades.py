import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

PASTA_MUSICAS = Path(__file__).parent / "musicas"
URL_BUSCA_LRCLIB = "https://lrclib.net/api/search"


def carregar_lista_de_musicas() -> list[dict]:
    lista_de_musicas = []

    if not PASTA_MUSICAS.exists():
        return lista_de_musicas

    for indice, pasta_da_musica in enumerate(sorted(PASTA_MUSICAS.iterdir())):
        arquivo_letra = pasta_da_musica / "letra.json"
        if not arquivo_letra.exists():
            continue

        with open(arquivo_letra, encoding="utf-8") as arquivo:
            dados_da_musica = json.load(arquivo)

        arquivo_audio = pasta_da_musica / dados_da_musica.get("arquivo_audio", "audio.mp3")
        audio_existe = arquivo_audio.exists()

        caminho_audio_relativo = arquivo_audio.relative_to(PASTA_MUSICAS).as_posix() if audio_existe else None

        lista_de_musicas.append({
            "caminho_do_json": str(arquivo_letra.resolve()),
            "pasta": pasta_da_musica,
            "titulo": dados_da_musica.get("titulo", pasta_da_musica.name),
            "artista": dados_da_musica.get("artista", ""),
            "caminho_audio": caminho_audio_relativo,
            "caminho_audio_absoluto": str(arquivo_audio.resolve()) if audio_existe else None,
            "linhas": dados_da_musica.get("linhas", []),
            "vocabulario": dados_da_musica.get("vocabulario", {}),
            "favorito": dados_da_musica.get("favorito", False),
            "ordem": dados_da_musica.get("ordem", indice),
        })

    return lista_de_musicas

def salvar_vocabulario_no_arquivo(caminho_do_json: str, vocabulario: dict) -> None:
    with open(caminho_do_json, encoding="utf-8") as arquivo:
        dados_da_musica = json.load(arquivo)

    dados_da_musica["vocabulario"] = vocabulario

    with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
        json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)


def salvar_metadados_no_arquivo(caminho_do_json: str, **campos) -> None:
    with open(caminho_do_json, encoding="utf-8") as arquivo:
        dados_da_musica = json.load(arquivo)

    dados_da_musica.update(campos)

    with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
        json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)


def encontrar_indice_da_linha_atual(linhas: list[dict], tempo_atual_segundos: float) -> int:
    indice_encontrado = 0

    for indice, linha in enumerate(linhas):
        if linha["tempo"] <= tempo_atual_segundos:
            indice_encontrado = indice
        else:
            break

    return indice_encontrado


def dividir_linha_em_palavras(texto: str) -> list[str]:
    return [pedaco for pedaco in texto.split(" ") if pedaco]


def normalizar_chave_de_palavra(palavra: str) -> str:
    return re.sub(r"^[^\wÀ-ÖØ-öø-ÿ]+|[^\wÀ-ÖØ-öø-ÿ]+$", "", palavra, flags=re.UNICODE).lower()


def normalizar_para_comparar(texto: str) -> str:
    texto_sem_acento = unicodedata.normalize("NFKD", texto.strip().lower())
    texto_sem_acento = "".join(c for c in texto_sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto_sem_acento).strip()


def formatar_tempo(segundos: float) -> str:
    segundos_inteiros = int(segundos)
    minutos = segundos_inteiros // 60
    resto_segundos = segundos_inteiros % 60
    return f"{minutos:02d}:{resto_segundos:02d}"


def extrair_titulo_e_artista(nome_pasta: str) -> tuple[str, str]:
    if " - " in nome_pasta:
        partes = nome_pasta.split(" - ", 1)
        return partes[1].strip(), partes[0].strip()

    titulo_limpo = nome_pasta.replace("-", " ").replace("_", " ").title()
    return titulo_limpo, ""


def buscar_letra_sincronizada(titulo: str, artista: str) -> str | None:
    parametros = urllib.parse.urlencode({"track_name": titulo, "artist_name": artista})
    url = f"{URL_BUSCA_LRCLIB}?{parametros}"
    requisicao = urllib.request.Request(url, headers={"User-Agent": "frenchlingo/1.0"})

    try:
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            resultados = json.loads(resposta.read().decode("utf-8"))
            for resultado in resultados:
                letra = resultado.get("syncedLyrics")
                if letra:
                    return letra
    except Exception:
        pass

    try:
        query_simples = urllib.parse.urlencode({"q": f"{titulo} {artista}"})
        url_simples = f"{URL_BUSCA_LRCLIB}?{query_simples}"
        req_simples = urllib.request.Request(url_simples, headers={"User-Agent": "frenchlingo/1.0"})
        with urllib.request.urlopen(req_simples, timeout=15) as resposta:
            resultados = json.loads(resposta.read().decode("utf-8"))
            for resultado in resultados:
                letra = resultado.get("syncedLyrics")
                if letra:
                    return letra
    except Exception:
        pass

    return None
