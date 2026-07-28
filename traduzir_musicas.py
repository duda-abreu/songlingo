import json
from pathlib import Path

from criar_musica import tentar_traduzir

PASTA_MUSICAS = Path(__file__).parent / "musicas"


def traduzir_musica(caminho_do_json: Path) -> tuple[int, int]:
    with open(caminho_do_json, encoding="utf-8") as arquivo:
        dados_da_musica = json.load(arquivo)

    linhas_traduzidas = 0
    palavras_traduzidas = 0

    for linha in dados_da_musica.get("linhas", []):
        if not linha.get("pt"):
            linha["pt"] = tentar_traduzir(linha["fr"], "pt")
            linhas_traduzidas += 1
            with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
                json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)
        if not linha.get("en"):
            linha["en"] = tentar_traduzir(linha["fr"], "en")
            linhas_traduzidas += 1
            with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
                json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)

    vocabulario = dados_da_musica.get("vocabulario", {})
    for chave, entrada in vocabulario.items():
        if chave.isdigit():
            continue
        if not entrada.get("pt"):
            entrada["pt"] = tentar_traduzir(chave, "pt")
            palavras_traduzidas += 1
            with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
                json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)
        if not entrada.get("en"):
            entrada["en"] = tentar_traduzir(chave, "en")
            palavras_traduzidas += 1
            with open(caminho_do_json, "w", encoding="utf-8") as arquivo:
                json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)

    return linhas_traduzidas, palavras_traduzidas


def traduzir_tudo():
    pastas = sorted(p for p in PASTA_MUSICAS.iterdir() if p.is_dir())
    print(f"Encontradas {len(pastas)} músicas em 'musicas/'.\n", flush=True)

    for pasta in pastas:
        caminho_do_json = pasta / "letra.json"
        if not caminho_do_json.exists():
            continue

        print(f"Traduzindo: {pasta.name}...", flush=True)
        try:
            linhas, palavras = traduzir_musica(caminho_do_json)
            print(f"  OK - {linhas} traducoes de linha, {palavras} de vocabulario.\n", flush=True)
        except Exception as erro:
            print(f"  ERRO em {pasta.name}: {erro}\n", flush=True)

    print("Traducao de todas as musicas concluida.", flush=True)


if __name__ == "__main__":
    traduzir_tudo()
