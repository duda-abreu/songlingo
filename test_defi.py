import tempfile
import unittest
from pathlib import Path

from defi_desktop import PainelDefi


class PaginaTeste:
    def update(self):
        pass


class DefiTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo = Path(self.pasta.name) / "progresso.json"
        self.painel = self.abrir()

    def abrir(self):
        return PainelDefi(PaginaTeste(), lambda _: "#888888", caminho_progresso=self.arquivo)

    def test_erros_persistem_e_revisao_abre_questao_original(self):
        painel = self.painel
        painel.opcao_selecionada = 0
        painel._conferir()
        painel._conferir()
        reaberto = self.abrir()
        self.assertEqual(reaberto.erros["portrait:0"]["erros"], 2)
        reaberto._mostrar_revisao()
        self.assertFalse(reaberto.corpo_curso.visible)
        reaberto._revisar_atividade(0, 0)
        self.assertTrue(reaberto.corpo_curso.visible)
        reaberto.opcao_selecionada = 1
        reaberto._conferir()
        final = self.abrir()
        self.assertTrue(final.erros["portrait:0"]["revisado"])
        self.assertIn("portrait:0", final.concluidas)
        self.assertEqual(final.erros["portrait:0"]["erros"], 2)

    def test_sem_resposta_nao_conta_como_erro(self):
        self.painel._conferir()
        self.assertEqual(self.painel.erros, {})

    def test_formatos_novos_renderizam_e_oral_exige_autoavaliacao(self):
        painel = self.painel
        for ui, unidade in enumerate(painel.curso):
            painel.unidade_atual = ui
            for ai, atividade in enumerate(unidade["atividades"]):
                painel.atividade_atual = ai
                painel._renderizar_atividade()
                if atividade.get("audio") and atividade.get("opcoes"):
                    self.assertEqual(len(painel.area_resposta.controls), len(atividade["opcoes"]) + 1)
                if atividade.get("oral"):
                    painel._conferir()
                    self.assertNotIn(painel._chave(), painel.concluidas)
                    for check in painel.checks_orais:
                        check.value = True
                    painel._conferir()
                    self.assertIn(painel._chave(), painel.concluidas)
        self.assertEqual(sum(len(u["atividades"]) for u in painel.curso), 171)

    def test_ocultar_resposta_reabilita_nova_tentativa(self):
        self.painel.opcao_selecionada = 1
        self.painel._conferir()
        self.painel._mostrar_resposta()
        self.painel._tentar_novamente()
        self.assertFalse(self.painel.gabarito.visible)
        self.assertTrue(self.painel.botao_conferir.visible)
        self.assertIsNone(self.painel.opcao_selecionada)


if __name__ == "__main__":
    unittest.main()
