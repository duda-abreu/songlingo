import json
from pathlib import Path

PASTA_MUSICAS = Path(__file__).parent / "musicas"
PASTA_SITE = Path(__file__).parent / "docs"


def montar_dados_do_site():
    musicas = []

    for pasta in sorted(PASTA_MUSICAS.iterdir()):
        caminho_json = pasta / "letra.json"
        if not caminho_json.exists():
            continue

        with open(caminho_json, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        musicas.append({
            "titulo": dados["titulo"],
            "artista": dados["artista"],
            "linhas": dados["linhas"],
            "vocabulario": {
                chave: entrada for chave, entrada in dados.get("vocabulario", {}).items()
                if not chave.isdigit()
            },
        })

    caminho_saida = PASTA_SITE / "dados.json"
    with open(caminho_saida, "w", encoding="utf-8") as arquivo:
        json.dump(musicas, arquivo, ensure_ascii=False, separators=(",", ":"))

    print(f"{len(musicas)} musicas exportadas pra {caminho_saida}")


if __name__ == "__main__":
    montar_dados_do_site()
