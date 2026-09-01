import json
import unittest
from pathlib import Path


RAIZ = Path(__file__).parent


class MusicasTest(unittest.TestCase):
    def test_carmen_usa_letra_completa_e_sincronizada(self):
        dados = json.loads(
            (RAIZ / "musicas" / "carmen" / "letra.json").read_text(encoding="utf-8")
        )
        linhas = dados["linhas"]

        self.assertEqual("L'amour est comme l'oiseau de Twitter", linhas[0]["fr"])
        self.assertEqual(2.5, linhas[0]["tempo"])
        self.assertEqual(5.63, linhas[1]["tempo"])
        self.assertEqual(sorted(linha["tempo"] for linha in linhas), [linha["tempo"] for linha in linhas])


if __name__ == "__main__":
    unittest.main()
