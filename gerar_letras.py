import json
import sys
from pathlib import Path

from criar_musica import (
    analisar_texto_lrc,
    montar_vocabulario,
    tentar_traduzir,
)
from utilidades import buscar_letra_sincronizada, extrair_titulo_e_artista

PASTA_MUSICAS = Path(__file__).parent / "musicas"


def processar_todas_as_pastas(traduzir_automaticamente: bool = False):
    if not PASTA_MUSICAS.exists():
        print("pasta 'musicas' não encontrada.")
        return

    pastas = [p for p in PASTA_MUSICAS.iterdir() if p.is_dir()]
    print(f"{len(pastas)} pastas em 'musicas/'. buscando letras...\n")

    for pasta in pastas:
        caminho_json = pasta / "letra.json"

        if caminho_json.exists() and caminho_json.stat().st_size > 50:
            print(f"{pasta.name} já tem letra.json, pulando.")
            continue

        titulo, artista = extrair_titulo_e_artista(pasta.name)
        print(f"buscando '{titulo}' ({artista})...")

        texto_lrc = buscar_letra_sincronizada(titulo, artista)

        if not texto_lrc:
            print(f"   não encontrei letra sincronizada pra '{titulo}'.")
            linhas = []
            vocabulario = {}
        else:
            linhas = analisar_texto_lrc(texto_lrc)
            if traduzir_automaticamente:
                for linha in linhas:
                    linha["pt"] = tentar_traduzir(linha["fr"], "pt")
                    linha["en"] = tentar_traduzir(linha["fr"], "en")
            else:
                for linha in linhas:
                    linha["pt"] = ""
                    linha["en"] = ""

            vocabulario = montar_vocabulario(linhas, traduzir_automaticamente)
            print(f"   achei {len(linhas)} linhas.")

        dados = {
            "titulo": titulo,
            "artista": artista,
            "arquivo_audio": "audio.mp3",
            "linhas": linhas,
            "vocabulario": vocabulario,
        }

        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)

        print(f"   salvo em: {caminho_json}\n")

    print("pronto.")


if __name__ == "__main__":
    traduzir = "--com-traducao" in sys.argv
    processar_todas_as_pastas(traduzir_automaticamente=traduzir)