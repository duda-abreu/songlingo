import json
import os
import random
import subprocess
import threading
import unicodedata
from pathlib import Path

import flet as ft
from curso_defi import carregar_curso


FONTE_TITULO = "Baloo 2"
FONTE_CORPO = "Nunito"


def _normalizar(texto: str) -> str:
    valor = unicodedata.normalize("NFD", (texto or "").lower())
    valor = "".join(letra for letra in valor if unicodedata.category(letra) != "Mn")
    return " ".join("".join(letra if letra.isalnum() else " " for letra in valor).split())


def _distancia(a: str, b: str) -> int:
    linha = list(range(len(b) + 1))
    for indice_a, letra_a in enumerate(a, 1):
        anterior = linha[0]
        linha[0] = indice_a
        for indice_b, letra_b in enumerate(b, 1):
            atual = linha[indice_b]
            linha[indice_b] = min(
                linha[indice_b] + 1,
                linha[indice_b - 1] + 1,
                anterior + (letra_a != letra_b),
            )
            anterior = atual
    return linha[-1]


def _resposta_aceita(resposta: str, esperadas: list[str]) -> bool:
    recebida = _normalizar(resposta)
    for esperada in esperadas:
        certa = _normalizar(esperada)
        limite = max(1, int(len(certa) * 0.07))
        if recebida == certa or _distancia(recebida, certa) <= limite:
            return True
    return False


class PainelDefi:
    def __init__(self, pagina: ft.Page, cor, ao_fechar=None):
        self.pagina = pagina
        self.cor = cor
        self.ao_fechar = ao_fechar
        self.curso = carregar_curso()
        self.unidade_atual = 0
        self.atividade_atual = 0
        self.concluidas: set[str] = set()
        self.opcao_selecionada: int | None = None
        self.conexoes_feitas: set[int] = set()
        self.conexao_esquerda: int | None = None
        self.conexao_direita: int | None = None
        self.botoes_associacao: dict[tuple[str, int], ft.Button] = {}

        self.nivel = ft.Text(weight=ft.FontWeight.BOLD, color=self.cor("destaque"))
        self.tema = ft.Text(size=12, color=self.cor("texto_secundario"))
        self.titulo = ft.Text(size=30, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600)
        self.estado_unidade = ft.Text(size=11, color=self.cor("texto_secundario"))
        self.progresso = ft.ProgressBar(
            value=0,
            height=6,
            bar_height=6,
            border_radius=6,
            color=self.cor("destaque"),
            bgcolor=self.cor("cartao_claro"),
        )

        self.lista_unidades = ft.Column(spacing=8, col={"xs": 12, "md": 3})

        self.documento_titulo = ft.Text(size=19, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600)
        self.documento_texto = ft.Text(size=15)
        self.ferramenta_titulo = ft.Text(size=18, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600)
        self.ferramenta_texto = ft.Text(size=14, color=self.cor("texto_secundario"))
        self.tipo_atividade = ft.Text(size=11, weight=ft.FontWeight.BOLD, color=self.cor("destaque"))
        self.passos = ft.Row(spacing=6, wrap=True)
        self.pergunta = ft.Text(size=20, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600)
        self.instrucao = ft.Text(size=13, color=self.cor("texto_secundario"))
        self.area_resposta = ft.Column(spacing=9, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.feedback = ft.Text(size=14, weight=ft.FontWeight.BOLD)
        self.gabarito = ft.Container(visible=False, border_radius=12, padding=12, bgcolor=self.cor("cartao_claro"))
        self.botao_mostrar = ft.TextButton("mostrar resposta", icon=ft.Icons.VISIBILITY_ROUNDED, on_click=self._mostrar_resposta)
        self.botao_tentar = ft.TextButton("ocultar e tentar de novo", icon=ft.Icons.VISIBILITY_OFF_ROUNDED, visible=False, on_click=self._tentar_novamente)
        self.botao_conferir = ft.Button("conferir", icon=ft.Icons.CHECK_ROUNDED, bgcolor=self.cor("destaque"), color="white", on_click=self._conferir)
        self.botao_proxima = ft.Button("continuar", icon=ft.Icons.ARROW_FORWARD_ROUNDED, visible=False, on_click=self._proxima)

        self.cartao_documento = self._cartao(
            "document déclencheur",
            ft.Column([self.documento_titulo, self.documento_texto], spacing=8),
        )
        self.cartao_ferramenta = self._cartao(
            "boîte à outils",
            ft.Column([self.ferramenta_titulo, self.ferramenta_texto], spacing=8),
        )
        self.cartao_atividade = self._cartao(
            "activité",
            ft.Column(
                [
                    ft.Row([self.tipo_atividade, self.passos], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    self.pergunta,
                    self.instrucao,
                    self.area_resposta,
                    self.feedback,
                    self.gabarito,
                    ft.Row(
                        [self.botao_mostrar, self.botao_tentar, self.botao_conferir, self.botao_proxima],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                    ),
                ],
                spacing=10,
            ),
        )

        self.lista = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                ft.Text("SONGLINGO", size=11, color=self.cor("destaque"), weight=ft.FontWeight.BOLD),
                ft.Text("parcours défi", size=42, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600),
                ft.Text("observe, compreenda, descubra a regra e use o francês numa situação real.", color=self.cor("texto_secundario")),
                self.progresso,
                ft.ResponsiveRow(
                    [
                        self.lista_unidades,
                        ft.Column(
                            [
                                ft.Row([self.nivel, self.tema], spacing=10, wrap=True),
                                self.titulo,
                                self.estado_unidade,
                                self.cartao_documento,
                                self.cartao_ferramenta,
                                self.cartao_atividade,
                            ],
                            col={"xs": 12, "md": 9},
                            spacing=16,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        ),
                    ],
                    spacing=22,
                    run_spacing=18,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
        )
        self.corpo_curso = self.lista.controls[-1]
        self.controle = ft.Container(expand=True, visible=False, content=self.lista)
        self._renderizar(atualizar=False)

    def _cartao(self, etiqueta: str, conteudo: ft.Control) -> ft.Control:
        return ft.Container(
            bgcolor=self.cor("cartao"),
            border_radius=18,
            padding=20,
            border=ft.Border.all(1, self.cor("cartao_claro")),
            content=ft.Column(
                [
                    ft.Text(etiqueta.upper(), size=11, color=self.cor("destaque"), weight=ft.FontWeight.BOLD),
                    conteudo,
                ],
                spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
        )

    def _chave(self, unidade: int | None = None, atividade: int | None = None) -> str:
        unidade = self.unidade_atual if unidade is None else unidade
        atividade = self.atividade_atual if atividade is None else atividade
        return f"{self.curso[unidade]['id']}:{atividade}"

    def _unidade_concluida(self, indice: int) -> bool:
        return all(self._chave(indice, atividade) in self.concluidas for atividade in range(len(self.curso[indice]["atividades"])))

    def _selecionar_unidade(self, indice):
        self.unidade_atual = indice
        self.atividade_atual = 0
        self._renderizar()

    def _renderizar_unidades(self):
        self.lista_unidades.controls.clear()
        nivel_anterior = None
        for indice, unidade in enumerate(self.curso):
            if unidade["nivel"] != nivel_anterior:
                nivel_anterior = unidade["nivel"]
                self.lista_unidades.controls.append(ft.Text(
                    "PASSERELLE B1" if nivel_anterior == "B1" else nivel_anterior,
                    size=12, color=self.cor("destaque"), weight=ft.FontWeight.BOLD,
                ))
            self.lista_unidades.controls.append(ft.Container(
                padding=12,
                border_radius=12,
                bgcolor=self.cor("cartao_claro") if indice == self.unidade_atual else "transparent",
                on_click=lambda e, i=indice: self._selecionar_unidade(i),
                ink=True,
                content=ft.Row([
                    ft.Text("✓" if self._unidade_concluida(indice) else f"{indice + 1:02}", color=self.cor("destaque"), size=12),
                    ft.Column([
                        ft.Text(unidade["titulo"], size=13, weight=ft.FontWeight.BOLD),
                        ft.Text(unidade["tema"], size=11, color=self.cor("texto_secundario")),
                    ], expand=True, spacing=3),
                ], spacing=10),
            ))

    def _renderizar(self, atualizar: bool = True):
        unidade = self.curso[self.unidade_atual]
        self.nivel.value = unidade["nivel"]
        self.tema.value = unidade["tema"]
        self.titulo.value = unidade["titulo"]
        self.estado_unidade.value = "✓ atelier concluído" if self._unidade_concluida(self.unidade_atual) else "em andamento"
        self.documento_titulo.value = unidade["documentoTitulo"]
        self.documento_texto.value = unidade["documento"]
        self.ferramenta_titulo.value = unidade["ferramentaTitulo"]
        self.ferramenta_texto.value = unidade["ferramenta"]
        total = sum(len(item["atividades"]) for item in self.curso)
        self.progresso.value = len(self.concluidas) / total
        self._renderizar_unidades()
        self._renderizar_atividade()
        if atualizar:
            self.pagina.update()

    def _renderizar_passos(self):
        self.passos.controls.clear()
        atividades = self.curso[self.unidade_atual]["atividades"]
        for indice, _ in enumerate(atividades):
            feito = self._chave(self.unidade_atual, indice) in self.concluidas
            atual = indice == self.atividade_atual
            self.passos.controls.append(
                ft.Container(
                    width=10,
                    height=10,
                    border_radius=10,
                    bgcolor=self.cor("acerto") if feito else (self.cor("destaque") if atual else "transparent"),
                    border=ft.Border.all(1, self.cor("destaque") if atual else self.cor("texto_secundario")),
                    tooltip=self.curso[self.unidade_atual]["atividades"][indice]["tipo"],
                    on_click=lambda e, i=indice: self._abrir_atividade(i),
                    ink=True,
                )
            )

    def _abrir_atividade(self, indice: int):
        self.atividade_atual = indice
        self._renderizar_atividade()
        self.pagina.update()

    def _renderizar_atividade(self):
        atividade = self.curso[self.unidade_atual]["atividades"][self.atividade_atual]
        self.opcao_selecionada = None
        self.conexoes_feitas.clear()
        self.conexao_esquerda = None
        self.conexao_direita = None
        self.botoes_associacao.clear()
        self.tipo_atividade.value = atividade["tipo"].upper()
        self.pergunta.value = atividade["pergunta"]
        self.instrucao.value = atividade.get("instrucao", "Escolha ou escreva a melhor resposta em francês.")
        self.feedback.value = ""
        self.gabarito.visible = False
        self.gabarito.content = None
        self.botao_mostrar.visible = True
        self.botao_tentar.visible = False
        self.botao_conferir.visible = "pares" not in atividade
        self.botao_conferir.content = "terminei" if atividade.get("modelo") else "conferir"
        self.botao_proxima.visible = False
        self.area_resposta.controls.clear()
        self.checks_orais = []
        if atividade.get("audio"):
            self.area_resposta.controls.append(ft.Button(
                "ouvir em francês", icon=ft.Icons.VOLUME_UP_ROUNDED,
                bgcolor=self.cor("destaque"), color="white",
                on_click=lambda e, texto=atividade["audio"]: self._ouvir(texto),
            ))

        if atividade.get("oral"):
            self.botao_conferir.content = "concluir prática oral"
            self.area_resposta.controls.append(ft.Text("Fale em voz alta e marque sua autoavaliação. Não há correção automática de pronúncia."))
            self.checks_orais = [ft.Checkbox(label=item, value=False) for item in atividade["checklist"]]
            self.area_resposta.controls.extend(self.checks_orais)
        elif atividade.get("opcoes"):
            for indice, opcao in enumerate(atividade["opcoes"]):
                botao = ft.Button(
                    opcao,
                    data=indice,
                    bgcolor=self.cor("fundo"),
                    color=self.cor("texto_principal"),
                    on_click=self._selecionar_opcao,
                )
                self.area_resposta.controls.append(botao)
        elif atividade.get("pares"):
            self._montar_associacoes(atividade)
        else:
            self.campo_resposta = ft.TextField(
                multiline=True,
                min_lines=2,
                max_lines=5,
                autofocus=False,
                border_radius=12,
                hint_text="rédige ta réponse en français" if atividade.get("modelo") else "écrivez en français",
                on_submit=None if atividade.get("modelo") else self._conferir,
            )
            self.area_resposta.controls.append(self.campo_resposta)
        self._renderizar_passos()

    def _selecionar_opcao(self, e):
        self.opcao_selecionada = int(e.control.data)
        for controle in self.area_resposta.controls:
            if isinstance(controle, ft.Button) and isinstance(controle.data, int):
                controle.bgcolor = self.cor("cartao_claro") if controle is e.control else self.cor("fundo")
        self.pagina.update()

    def _montar_associacoes(self, atividade: dict):
        esquerda = list(enumerate(par[0] for par in atividade["pares"]))
        direita = list(enumerate(par[1] for par in atividade["pares"]))
        random.shuffle(esquerda)
        random.shuffle(direita)
        colunas = []
        for lado, itens in (("esquerda", esquerda), ("direita", direita)):
            coluna = ft.Column(spacing=8, expand=True)
            for indice, texto in itens:
                botao = ft.Button(
                    texto,
                    data=(lado, indice),
                    bgcolor=self.cor("fundo"),
                    color=self.cor("texto_principal"),
                    on_click=lambda e, l=lado, i=indice: self._selecionar_associacao(e, l, i, atividade),
                )
                self.botoes_associacao[(lado, indice)] = botao
                coluna.controls.append(botao)
            colunas.append(coluna)
        self.area_resposta.controls.append(ft.Row(colunas, spacing=10, vertical_alignment=ft.CrossAxisAlignment.START))

    def _selecionar_associacao(self, e, lado: str, indice: int, atividade: dict):
        if indice in self.conexoes_feitas:
            return
        for (lado_botao, indice_botao), botao in self.botoes_associacao.items():
            if lado_botao == lado and indice_botao not in self.conexoes_feitas:
                botao.bgcolor = self.cor("fundo")
        e.control.bgcolor = self.cor("cartao_claro")
        if lado == "esquerda":
            self.conexao_esquerda = indice
        else:
            self.conexao_direita = indice
        if self.conexao_esquerda is None or self.conexao_direita is None:
            self.pagina.update()
            return
        if self.conexao_esquerda == self.conexao_direita:
            certo = self.conexao_esquerda
            self.conexoes_feitas.add(certo)
            for lado_certo in ("esquerda", "direita"):
                botao = self.botoes_associacao[(lado_certo, certo)]
                botao.disabled = True
                botao.bgcolor = self.cor("cartao_claro")
                botao.color = self.cor("acerto")
            self.feedback.value = "bonne association !"
            self.feedback.color = self.cor("acerto")
            if len(self.conexoes_feitas) == len(atividade["pares"]):
                self.feedback.value = "tout est bien relié !"
                self._marcar_concluida()
        else:
            self.feedback.value = "essa ligação não combina — tente outra."
            self.feedback.color = self.cor("erro")
            for lado_errado, indice_errado in (("esquerda", self.conexao_esquerda), ("direita", self.conexao_direita)):
                self.botoes_associacao[(lado_errado, indice_errado)].bgcolor = self.cor("fundo")
        self.conexao_esquerda = None
        self.conexao_direita = None
        self.pagina.update()

    def _ouvir(self, texto: str):
        self.feedback.value = "reproduzindo em francês…"
        self.feedback.color = self.cor("destaque")
        self.pagina.update()
        def reproduzir():
            try:
                sucesso = self._falar_windows(texto)
            except (OSError, subprocess.TimeoutExpired):
                sucesso = False
            self.pagina.run_task(self._finalizar_audio, sucesso)
        threading.Thread(target=reproduzir, daemon=True).start()

    async def _finalizar_audio(self, sucesso):
        self.feedback.value = "Áudio concluído. Pode ouvir novamente." if sucesso else "Não foi possível reproduzir. Verifique se há uma voz francesa instalada no Windows."
        self.feedback.color = self.cor("destaque") if sucesso else self.cor("erro")
        self.pagina.update()

    @staticmethod
    def _falar_windows(texto: str):
        ambiente = os.environ.copy()
        ambiente["SONGLINGO_DEFI_TEXTO"] = texto
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$v=$s.GetInstalledVoices()|Where-Object {$_.VoiceInfo.Culture.Name -like 'fr-*'}|Select-Object -First 1; "
            "if(!$v){exit 2}; $s.SelectVoice($v.VoiceInfo.Name); "
            "$s.Rate=-2; $s.Speak($env:SONGLINGO_DEFI_TEXTO); $s.Dispose()"
        )
        resultado = subprocess.run(["powershell", "-NoProfile", "-Command", script], env=ambiente,
                                   capture_output=True, timeout=120,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return resultado.returncode == 0

    def _conferir(self, e=None):
        atividade = self.curso[self.unidade_atual]["atividades"][self.atividade_atual]
        if atividade.get("oral"):
            if not all(item.value for item in self.checks_orais):
                self.feedback.value = "Pratique os pontos restantes antes de concluir sua autoavaliação."
                self.feedback.color = self.cor("erro")
            else:
                self.feedback.value = "Prática oral concluída por autoavaliação."
                self.feedback.color = self.cor("acerto")
                self._marcar_concluida()
            self.pagina.update()
            return
        if atividade.get("modelo"):
            minimo = atividade.get("minPalavras", 5)
            if len(_normalizar(self.campo_resposta.value).split()) < minimo:
                self.feedback.value = f"Desenvolva sua resposta até pelo menos {minimo} palavras."
                self.feedback.color = self.cor("erro")
                self.pagina.update()
                return
            self.feedback.value = "Texto registrado. Compare com o modelo e os critérios; esta produção é autoavaliada."
            self.feedback.color = self.cor("acerto")
            self._mostrar_checklist(atividade)
            self._marcar_concluida()
            self.pagina.update()
            return

        if atividade.get("opcoes"):
            if self.opcao_selecionada is None:
                self.feedback.value = "escolha uma opção."
                self.feedback.color = self.cor("erro")
                self.pagina.update()
                return
            correta = self.opcao_selecionada == atividade["correta"]
        else:
            if not _normalizar(self.campo_resposta.value):
                self.feedback.value = "escreva uma resposta primeiro."
                self.feedback.color = self.cor("erro")
                self.pagina.update()
                return
            correta = _resposta_aceita(self.campo_resposta.value, atividade["respostas"])

        if correta:
            self.feedback.value = f"bien vu ! {atividade.get('explicacao', '')}"
            self.feedback.color = self.cor("acerto")
            self._marcar_concluida()
        else:
            self.feedback.value = "pas encore — observe o documento e tente outra vez."
            self.feedback.color = self.cor("erro")
        self.pagina.update()

    def _marcar_concluida(self):
        self.concluidas.add(self._chave())
        self._renderizar_unidades()
        total = sum(len(item["atividades"]) for item in self.curso)
        self.progresso.value = len(self.concluidas) / total
        self.botao_conferir.visible = False
        self.botao_proxima.visible = True
        self.estado_unidade.value = "✓ atelier concluído" if self._unidade_concluida(self.unidade_atual) else "em andamento"
        self._renderizar_passos()

    def _mostrar_checklist(self, atividade: dict):
        self.gabarito.content = ft.Column(
            [ft.Text("à vérifier", weight=ft.FontWeight.BOLD)]
            + [ft.Text(f"• {item}") for item in atividade["checklist"]],
            spacing=4,
        )
        self.gabarito.visible = True

    def _mostrar_resposta(self, e=None):
        atividade = self.curso[self.unidade_atual]["atividades"][self.atividade_atual]
        if atividade.get("modelo"):
            controles = [ft.Text("exemple possible", weight=ft.FontWeight.BOLD), ft.Text(atividade["modelo"])]
            controles += [ft.Text(f"• {item}") for item in atividade["checklist"]]
        elif atividade.get("pares"):
            controles = [ft.Text("associations", weight=ft.FontWeight.BOLD)]
            controles += [ft.Text(f"• {esquerda} → {direita}") for esquerda, direita in atividade["pares"]]
        else:
            resposta = atividade["opcoes"][atividade["correta"]] if atividade.get("opcoes") else atividade["resposta"]
            controles = [ft.Text("réponse", weight=ft.FontWeight.BOLD), ft.Text(resposta), ft.Text(atividade.get("explicacao", ""), size=12)]
        self.gabarito.content = ft.Column(controles, spacing=5)
        self.gabarito.visible = True
        self.botao_mostrar.visible = False
        self.botao_tentar.visible = True
        self.pagina.update()

    def _tentar_novamente(self, e=None):
        self._renderizar_atividade()
        self.pagina.update()

    def _proxima(self, e=None):
        ultima = len(self.curso[self.unidade_atual]["atividades"]) - 1
        if self.atividade_atual < ultima:
            self.atividade_atual += 1
        elif self.unidade_atual < len(self.curso) - 1:
            self.unidade_atual += 1
            self.atividade_atual = 0
        self._renderizar()

    def _fechar(self, e=None):
        if self.ao_fechar:
            self.ao_fechar()

    def mostrar(self):
        self.controle.visible = True
        self._renderizar(atualizar=False)

    def ocultar(self):
        self.controle.visible = False

    def aplicar_tema(self):
        for cartao in (self.cartao_documento, self.cartao_ferramenta, self.cartao_atividade):
            cartao.bgcolor = self.cor("cartao")
            cartao.border = ft.Border.all(1, self.cor("cartao_claro"))
        self._renderizar(atualizar=False)
