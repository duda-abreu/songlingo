import unittest

from estudo import (
    avaliar_resposta,
    exercicios_ingles_para_frances,
    fim_do_trecho,
    indices_validos_para_ditado,
    normalizar_resposta,
    normalizar_equivalencias_francesas,
    parece_frances,
)


class EstudoTest(unittest.TestCase):
    def test_normaliza_acentos_pontuacao_e_espacos(self):
        self.assertEqual(normalizar_resposta("  Évidemment,  j’aime! "), "evidemment j'aime")

    def test_resposta_exata_sem_acentos_e_certa(self):
        resultado = avaliar_resposta("je t'aime deja", "Je t’aime déjà")
        self.assertEqual(resultado["status"], "certo")

    def test_resposta_parcial_mostra_palavras_ausentes(self):
        resultado = avaliar_resposta("je veux des fleurs", "je veux toujours des fleurs")
        self.assertEqual(resultado["status"], "quase")
        self.assertEqual(resultado["faltaram"], ["toujours"])

    def test_resposta_distante_e_errada(self):
        self.assertEqual(avaliar_resposta("bonjour", "je veux des fleurs")["status"], "errado")

    def test_filtra_linhas_ruins_para_ditado(self):
        linhas = [{"fr": "Ah"}, {"fr": "Je veux des fleurs"}, {"fr": "Bring me flowers"}, {"fr": ""}]
        self.assertEqual(indices_validos_para_ditado(linhas), [1])

    def test_detecta_idioma_de_trechos_mistos(self):
        self.assertTrue(parece_frances("C'est juste que j'aime ta fleur"))
        self.assertFalse(parece_frances("Bring your sweat to my bed tonight"))

    def test_fim_do_trecho_usa_proxima_linha(self):
        linhas = [{"tempo": 3.0}, {"tempo": 6.0}]
        self.assertAlmostEqual(fim_do_trecho(linhas, 0), 5.92)

    def test_exercicios_usam_traducao_ingles_frances_e_ignoram_linha_inglesa(self):
        linhas = [
            {"en": "I want flowers", "fr": "Je veux des fleurs"},
            {"en": "Bring me flowers", "fr": "Bring me flowers"},
        ]
        exercicios = exercicios_ingles_para_frances(linhas)
        self.assertIn({"en": "I want flowers", "fr": "Je veux des fleurs", "origem": "música"}, exercicios)
        self.assertNotIn({"en": "Bring me flowers", "fr": "Bring me flowers", "origem": "música"}, exercicios)

    def test_traducao_aceita_erro_de_acento(self):
        resultado = avaliar_resposta("Ou vas tu ce soir", "Où vas-tu ce soir ?")
        self.assertEqual(resultado["status"], "certo")

    def test_traducao_aceita_pergunta_informal_sem_est_ce_que(self):
        resultado = avaliar_resposta("Tu peux m'aider ?", "Est-ce que tu peux m'aider ?")
        self.assertEqual(resultado["status"], "certo")

    def test_traducao_aceita_frances_falado_sem_ne(self):
        resultado = avaliar_resposta("Je sais pas", "Je ne sais pas")
        self.assertEqual(resultado["status"], "certo")

    def test_normaliza_pergunta_com_inversao(self):
        self.assertEqual(
            normalizar_equivalencias_francesas("Peux-tu m'aider ?"),
            normalizar_equivalencias_francesas("Est-ce que tu peux m'aider ?"),
        )


if __name__ == "__main__":
    unittest.main()
