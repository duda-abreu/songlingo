"""Conteúdo compartilhado entre o aplicativo e o site."""

import json
from pathlib import Path


RAIZ = Path(__file__).resolve().parent


def carregar_curso():
    curso = json.loads((RAIZ / "defi_data.json").read_text(encoding="utf-8"))
    pratica = json.loads((RAIZ / "defi_pratica.json").read_text(encoding="utf-8"))
    for unidade in curso:
        # Acrescentar preserva os índices do progresso já salvo no site.
        unidade["atividades"].extend(pratica.get(unidade["id"], []))
    return curso


if __name__ == "__main__":
    curso = carregar_curso()
    conteudo = "// Gerado por python curso_defi.py.\nwindow.CURSO_DEFI = "
    conteudo += json.dumps(curso, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (RAIZ / "docs" / "defi-data.js").write_text(conteudo, encoding="utf-8")
    print(f"{len(curso)} unidades, {sum(len(u['atividades']) for u in curso)} atividades")
