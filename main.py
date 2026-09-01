import asyncio
import json
import random
import shutil
import subprocess
import threading
from pathlib import Path

import flet as ft
import pygame
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from criar_musica import analisar_texto_lrc, montar_vocabulario, tentar_traduzir
from defi_desktop import PainelDefi
from estudo import avaliar_resposta, exercicios_ingles_para_frances, fim_do_trecho, indices_validos_para_ditado
from utilidades import (
    buscar_letra_sincronizada,
    carregar_lista_de_musicas,
    dividir_linha_em_palavras,
    encontrar_indice_da_linha_atual,
    extrair_titulo_e_artista,
    formatar_tempo,
    normalizar_chave_de_palavra,
    normalizar_para_comparar,
    salvar_metadados_no_arquivo,
    salvar_vocabulario_no_arquivo,
)

PALETA = {
    "claro": {
        "destaque": "#ff8fc4",
        "acerto": "#4caf82",
        "erro": "#f0648a",
        "texto_secundario": "#a99aa8",
        "texto_principal": "#4a3b47",
        "fundo": "#f8f4fb",
        "fundo_lateral": "#ffffff",
        "cartao": "#ffffff",
        "cartao_claro": "#ffe1ee",
        "palavra_clicavel": "#fbf3fa",
        "sombra": "#e8d9ea",
    },
    "escuro": {
        "destaque": "#ff8fc4",
        "acerto": "#5fd39c",
        "erro": "#ff7fa3",
        "texto_secundario": "#c2aec0",
        "texto_principal": "#f5eaf3",
        "fundo": "#1c1420",
        "fundo_lateral": "#150e18",
        "cartao": "#2b2030",
        "cartao_claro": "#40293c",
        "palavra_clicavel": "#332638",
        "sombra": "#000000",
    },
}

FONTE_TITULO = "Baloo 2"
FONTE_CORPO = "IBM Plex Mono"

MODO_OUVIR = "ouvir"
MODO_ESTUDAR = "estudar"
MODO_DITADO = "ditado"
MODO_TRADUZIR = "traduzir"
MODO_REVISAR = "revisar"
MODO_DEFI = "defi"


async def main(pagina: ft.Page):
    lista_de_musicas = carregar_lista_de_musicas()
    estado = {
        "musica_selecionada": None,
        "indice_linha_atual": -1,
        "linha_selecionada": None,
        "seguir_letra_automaticamente": True,
        "tocando": False,
        "reproducao_iniciada": False,
        "offset_pygame": 0.0,
        "duracao_audio": 0.0,
        "modo": MODO_OUVIR,
        "idioma_de_estudo": "pt",
        "acertos": 0,
        "tentativas": 0,
        "indice_ditado": None,
        "fim_trecho_ditado": None,
        "questoes_ditado": 0,
        "exercicio_traducao": None,
        "escuro": True,
        "filtro_busca": "",
        "aleatorio": False,
        "filtro_palavras": "",
        "ordenar_alfabeticamente": False,
    }

    def cor(chave: str) -> str:
        return PALETA["escuro" if estado["escuro"] else "claro"][chave]

    pagina.title = "aprenda francês cantando"
    pagina.fonts = {
        FONTE_TITULO: "https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700&display=swap",
        FONTE_CORPO: "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap",
    }
    pagina.theme_mode = ft.ThemeMode.DARK if estado["escuro"] else ft.ThemeMode.LIGHT
    pagina.theme = ft.Theme(font_family=FONTE_CORPO, color_scheme_seed=cor("destaque"))
    pagina.bgcolor = cor("fundo")
    pagina.padding = 0
    pagina.window.width = 1100
    pagina.window.height = 780

    cartoes_criados = []

    def criar_cartao(titulo: str, conteudo: ft.Control, expandir: bool = False, compacto: bool = False) -> ft.Container:
        texto_etiqueta = ft.Text(
            f"˚ {titulo}", size=13, font_family=FONTE_TITULO, color=cor("destaque"),
            weight=ft.FontWeight.W_600, no_wrap=True,
        )
        etiqueta = ft.Container(
            padding=ft.Padding.symmetric(horizontal=13, vertical=5),
            border_radius=30,
            bgcolor=cor("cartao_claro"),
            content=texto_etiqueta,
            visible=not compacto,
        )
        externo = ft.Container(
            expand=expandir,
            border_radius=26 if not compacto else 20,
            bgcolor=cor("cartao"),
            padding=16 if not compacto else ft.Padding.symmetric(horizontal=18, vertical=8),
            shadow=ft.BoxShadow(blur_radius=22, spread_radius=-4, offset=ft.Offset(0, 8), color=cor("sombra")),
            content=ft.Column(
                expand=expandir,
                spacing=0 if compacto else 10,
                controls=[
                    etiqueta,
                    ft.Container(expand=expandir, content=conteudo),
                ],
            ),
        )
        cartoes_criados.append((externo, etiqueta, texto_etiqueta))
        return externo

    pygame.mixer.init()
    pagina.on_disconnect = lambda e: pygame.mixer.music.stop()

    titulo_musica_texto = ft.Text("selecione uma música", size=32, font_family=FONTE_CORPO, color=cor("texto_principal"))
    artista_musica_texto = ft.Text("", size=16, color=cor("texto_secundario"))

    capa_musica_cabecalho = ft.Container(
        width=80, height=80, bgcolor=cor("cartao_claro"), border_radius=22, alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        shadow=ft.BoxShadow(blur_radius=14, spread_radius=-4, offset=ft.Offset(0, 5), color=cor("sombra")),
        content=ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color=cor("destaque"), size=32),
    )

    titulo_mini_texto = ft.Text(
        "selecione uma música", size=12, font_family=FONTE_CORPO, max_lines=2,
    )
    artista_mini_texto = ft.Text(
        "", size=10, color=cor("texto_secundario"),
        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
    )
    capa_mini = ft.Container(
        width=48, height=48, bgcolor=cor("cartao_claro"), border_radius=14, alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color=cor("destaque"), size=22),
    )

    def ao_clicar_favoritar_player(e):
        if estado["musica_selecionada"]:
            ao_favoritar(estado["musica_selecionada"])

    def ao_clicar_excluir_player(e):
        if estado["musica_selecionada"]:
            pagina.run_task(confirmar_exclusao_musica, estado["musica_selecionada"])

    botao_favoritar_player = ft.IconButton(
        icon=ft.Icons.FAVORITE_BORDER_ROUNDED, icon_color=cor("texto_secundario"), icon_size=16,
        tooltip="favoritar", on_click=ao_clicar_favoritar_player,
    )
    botao_excluir_player = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED, icon_color=cor("texto_secundario"), icon_size=16,
        tooltip="remover música", on_click=ao_clicar_excluir_player,
    )

    coluna_letra = ft.ListView(expand=True, spacing=4, auto_scroll=False, padding=10)
    coluna_letra_ouvir = ft.Column(
        expand=True, spacing=6,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False,
    )
    coluna_palavras_aprendidas = ft.ListView(expand=True, spacing=4, auto_scroll=False, padding=10)

    painel_traducao = ft.Container(
        content=ft.Text(
            "clique em uma linha da letra para ver a tradução aqui.",
            color=cor("texto_secundario"),
            italic=True,
            size=18,
            font_family=FONTE_CORPO,
        ),
    )

    texto_placar = ft.Text("acertos: 0 / 0", size=15, font_family=FONTE_CORPO, color=cor("texto_secundario"))

    texto_ditado_etapa = ft.Text("trecho 1", size=13, color=cor("texto_secundario"))
    texto_ditado_instrucao = ft.Text(
        "ouça o trecho e escreva exatamente o que entendeu em francês",
        size=18,
        font_family=FONTE_CORPO,
        text_align=ft.TextAlign.CENTER,
    )
    campo_ditado = ft.TextField(
        label="o que você ouviu?",
        hint_text="escreva em francês",
        multiline=True,
        min_lines=2,
        max_lines=4,
        autofocus=True,
        border_radius=12,
    )
    texto_feedback_ditado = ft.Text("", size=16, font_family=FONTE_CORPO, selectable=True)
    texto_resposta_ditado = ft.Text("", size=17, font_family=FONTE_CORPO, selectable=True)
    progresso_ditado = ft.ProgressBar(value=0, color=cor("destaque"), bgcolor=cor("cartao_claro"))
    botao_ouvir_ditado = ft.Button("ouvir trecho", icon=ft.Icons.PLAY_ARROW_ROUNDED)
    botao_repetir_ditado = ft.IconButton(icon=ft.Icons.REPLAY_ROUNDED, tooltip="ouvir novamente")
    botao_revelar_ditado = ft.TextButton("não sei", icon=ft.Icons.VISIBILITY_ROUNDED)
    botao_pular_ditado = ft.TextButton("pular", icon=ft.Icons.SKIP_NEXT_ROUNDED)
    botao_conferir_ditado = ft.Button("conferir", icon=ft.Icons.CHECK_ROUNDED, bgcolor=cor("destaque"), color="white")
    botao_proximo_ditado = ft.Button("próximo", icon=ft.Icons.SKIP_NEXT_ROUNDED, visible=False)
    painel_ditado = criar_cartao(
        "ditado de escuta",
        ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Row([texto_ditado_etapa, ft.Container(expand=True), botao_repetir_ditado]),
                progresso_ditado,
                ft.Container(height=8),
                texto_ditado_instrucao,
                botao_ouvir_ditado,
                campo_ditado,
                texto_feedback_ditado,
                texto_resposta_ditado,
                ft.Row(
                    [botao_revelar_ditado, botao_pular_ditado, ft.Container(expand=True), botao_conferir_ditado, botao_proximo_ditado],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
        ),
        expandir=True,
    )
    painel_ditado.visible = False

    texto_frase_ingles = ft.Text(
        "",
        size=24,
        weight=ft.FontWeight.W_600,
        font_family=FONTE_CORPO,
        text_align=ft.TextAlign.CENTER,
        selectable=True,
    )
    texto_origem_traducao = ft.Text("", size=12, color=cor("texto_secundario"), italic=True)
    campo_traducao_frances = ft.TextField(
        label="tradução em francês",
        hint_text="écrivez en français",
        multiline=True,
        min_lines=2,
        max_lines=4,
        autofocus=True,
        border_radius=12,
    )
    texto_feedback_traducao = ft.Text("", size=16, font_family=FONTE_CORPO, selectable=True)
    texto_gabarito_traducao = ft.Text("", size=17, font_family=FONTE_CORPO, selectable=True)
    botao_revelar_traducao = ft.TextButton("mostrar resposta", icon=ft.Icons.VISIBILITY_ROUNDED)
    botao_tentar_novamente_traducao = ft.TextButton(
        "ocultar e tentar de novo", icon=ft.Icons.VISIBILITY_OFF_ROUNDED, visible=False
    )
    botao_pular_traducao = ft.TextButton("pular", icon=ft.Icons.SKIP_NEXT_ROUNDED)
    botao_conferir_traducao = ft.Button("conferir", icon=ft.Icons.CHECK_ROUNDED, bgcolor=cor("destaque"), color="white")
    botao_proxima_traducao = ft.Button("próxima", icon=ft.Icons.SKIP_NEXT_ROUNDED, visible=False)
    painel_traduzir = criar_cartao(
        "inglês → francês",
        ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Row([ft.Container(expand=True), texto_origem_traducao]),
                ft.Text("traduza para francês", size=15, color=cor("texto_secundario")),
                texto_frase_ingles,
                campo_traducao_frances,
                texto_feedback_traducao,
                texto_gabarito_traducao,
                ft.Row(
                    [botao_revelar_traducao, botao_tentar_novamente_traducao, botao_pular_traducao, ft.Container(expand=True), botao_conferir_traducao, botao_proxima_traducao],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
        ),
        expandir=True,
    )
    painel_traduzir.visible = False

    slider_progresso = ft.Slider(min=0, max=100, value=0, active_color=cor("destaque"), expand=True)
    texto_tempo_atual = ft.Text("00:00", size=11, color=cor("texto_secundario"))
    texto_tempo_total = ft.Text("00:00", size=11, color=cor("texto_secundario"))

    botao_anterior = ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_size=18, icon_color=cor("texto_secundario"))
    botao_play_pause = ft.IconButton(
        icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=26, icon_color=cor("destaque"),
    )
    botao_proximo = ft.IconButton(icon=ft.Icons.SKIP_NEXT_ROUNDED, icon_size=18, icon_color=cor("texto_secundario"))
    botao_aleatorio = ft.IconButton(
        icon=ft.Icons.SHUFFLE_ROUNDED,
        icon_size=15,
        icon_color=cor("texto_secundario"),
        tooltip="ativar modo aleatório e trocar de música",
    )

    def ao_mudar_volume(e):
        pygame.mixer.music.set_volume(float(e.control.value) / 100)

    slider_volume = ft.Slider(
        min=0, max=100, value=70, width=150, active_color=cor("destaque"), on_change=ao_mudar_volume,
    )
    pygame.mixer.music.set_volume(0.7)

    switch_seguir_letra = ft.Switch(
        label="traduzir linha atual automaticamente", value=True, active_color=cor("destaque"),
    )

    painel_defi = PainelDefi(pagina, cor)

    def criar_botao_de_modo(rotulo: str, valor_do_modo: str):
        eh_ativo = estado["modo"] == valor_do_modo
        return ft.Container(
            content=ft.Text(rotulo, size=14, font_family=FONTE_CORPO, weight=ft.FontWeight.W_600, color="white" if eh_ativo else cor("texto_principal")),
            bgcolor=cor("destaque") if eh_ativo else cor("cartao"),
            border_radius=30,
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            shadow=ft.BoxShadow(blur_radius=12, spread_radius=-6, offset=ft.Offset(0, 4), color=cor("sombra")) if eh_ativo else None,
            on_click=lambda e, m=valor_do_modo: mudar_modo(m),
            ink=True,
        )

    linha_seletor_de_modo = ft.Row(spacing=8, wrap=True)

    def criar_botao_de_idioma(rotulo: str, valor_do_idioma: str):
        eh_ativo = estado["idioma_de_estudo"] == valor_do_idioma
        return ft.Container(
            content=ft.Text(rotulo, size=16, font_family=FONTE_CORPO, weight=ft.FontWeight.W_600 if eh_ativo else None, color=cor("destaque") if eh_ativo else cor("texto_secundario")),
            bgcolor=cor("cartao_claro") if eh_ativo else "transparent",
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=13, vertical=6),
            on_click=lambda e, i=valor_do_idioma: mudar_idioma_de_estudo(i),
            ink=True,
        )

    linha_seletor_de_idioma = ft.Row(spacing=6)

    def redesenhar_seletores():
        linha_seletor_de_modo.controls = [
            criar_botao_de_modo("ouvir", MODO_OUVIR),
            criar_botao_de_modo("modo estudo", MODO_ESTUDAR),
            criar_botao_de_modo("ditado", MODO_DITADO),
            criar_botao_de_modo("inglês → francês", MODO_TRADUZIR),
            criar_botao_de_modo("palavras aprendidas", MODO_REVISAR),
            criar_botao_de_modo("parcours défi A2 → B1", MODO_DEFI),
        ]
        linha_seletor_de_idioma.controls = [
            ft.Text("praticar em:", size=15, font_family=FONTE_CORPO, color=cor("texto_secundario")),
            criar_botao_de_idioma("português", "pt"),
            criar_botao_de_idioma("english", "en"),
        ]
        linha_seletor_de_idioma.visible = estado["modo"] in (MODO_ESTUDAR, MODO_REVISAR)
        switch_seguir_letra.visible = estado["modo"] == MODO_OUVIR
        painel_traducao.visible = estado["modo"] == MODO_OUVIR
        texto_placar.visible = estado["modo"] == MODO_ESTUDAR
        if estado["modo"] == MODO_ESTUDAR:
            texto_placar.value = f"acertos: {estado['acertos']} / {estado['tentativas']}"
        janela_letra.visible = estado["modo"] in (MODO_OUVIR, MODO_ESTUDAR)
        painel_ditado.visible = estado["modo"] == MODO_DITADO
        painel_traduzir.visible = estado["modo"] == MODO_TRADUZIR
        janela_palavras_aprendidas.visible = estado["modo"] == MODO_REVISAR
        coluna_letra.visible = estado["modo"] == MODO_ESTUDAR
        coluna_letra_ouvir.visible = estado["modo"] == MODO_OUVIR
        modo_defi = estado["modo"] == MODO_DEFI
        if modo_defi:
            painel_defi.mostrar()
        else:
            painel_defi.ocultar()
        cabecalho_musica.visible = not modo_defi
        linha_auxiliar_estudo.visible = not modo_defi
        linha_switch_seguir.visible = estado["modo"] == MODO_OUVIR
        cartao_traducao.visible = estado["modo"] == MODO_OUVIR

    def mudar_modo(novo_modo: str):
        estado["modo"] = novo_modo
        redesenhar_seletores()
        atualizar_letra_na_tela()
        atualizar_lista_de_palavras_aprendidas()
        if novo_modo == MODO_DITADO:
            preparar_ditado()
        elif novo_modo == MODO_TRADUZIR:
            preparar_traducao()
        pagina.update()

    def mudar_idioma_de_estudo(novo_idioma: str):
        estado["idioma_de_estudo"] = novo_idioma
        redesenhar_seletores()
        atualizar_lista_de_palavras_aprendidas()
        pagina.update()

    def mostrar_traducao_da_linha(indice: int):
        if estado["musica_selecionada"] is None:
            return

        linhas = estado["musica_selecionada"]["linhas"]
        if indice < 0 or indice >= len(linhas):
            return

        linha = linhas[indice]
        estado["linha_selecionada"] = indice

        painel_traducao.content = ft.Column(
            spacing=8,
            controls=[
                ft.Text(linha["fr"], size=16, italic=True, font_family=FONTE_CORPO, color=cor("texto_secundario")),
                ft.Divider(height=1, color=cor("cartao_claro")),
                ft.Row([ft.Text("pt", size=13, font_family=FONTE_CORPO, color=cor("destaque"), weight=ft.FontWeight.BOLD), ft.Text(linha.get("pt", ""), size=18, font_family=FONTE_CORPO, weight=ft.FontWeight.W_600, expand=True)]),
                ft.Row([ft.Text("en", size=13, font_family=FONTE_CORPO, color=cor("destaque"), weight=ft.FontWeight.BOLD), ft.Text(linha.get("en", ""), size=18, font_family=FONTE_CORPO, color=cor("texto_principal"), expand=True)]),
            ],
        )
        atualizar_letra_na_tela()
        pagina.update()

    campo_resposta = ft.TextField(label="sua tradução", autofocus=True)
    texto_feedback_dialogo = ft.Text("", size=14)
    texto_palavra_dialogo = ft.Text("", size=32, font_family=FONTE_CORPO, color=cor("destaque"))

    estado_dialogo = {"chave_palavra": None, "palavra_original": None}

    def abrir_dialogo_da_palavra(palavra_bruta: str):
        chave = normalizar_chave_de_palavra(palavra_bruta)
        if not chave:
            return

        estado_dialogo["chave_palavra"] = chave
        estado_dialogo["palavra_original"] = palavra_bruta

        texto_palavra_dialogo.value = palavra_bruta
        campo_resposta.value = ""
        campo_resposta.border_color = None
        texto_feedback_dialogo.value = ""
        texto_feedback_dialogo.color = cor("texto_secundario")

        pagina.show_dialog(dialogo_palavra)
        pagina.update()

    async def conferir_resposta(e):
        vocabulario = estado["musica_selecionada"]["vocabulario"]
        chave = estado_dialogo["chave_palavra"]
        entrada = vocabulario.get(chave)

        idioma = estado["idioma_de_estudo"]

        if entrada is None or not entrada.get(idioma):
            resposta_do_usuario = campo_resposta.value.strip()
            texto_feedback_dialogo.value = "conferindo..."
            texto_feedback_dialogo.color = cor("texto_secundario")
            pagina.update()

            traducao_referencia = await asyncio.to_thread(tentar_traduzir, chave, idioma)
            referencia_normalizada = normalizar_para_comparar(traducao_referencia) if traducao_referencia else ""

            vocabulario[chave] = vocabulario.get(chave, {"pt": "", "en": ""})

            if traducao_referencia and referencia_normalizada != normalizar_para_comparar(resposta_do_usuario):
                vocabulario[chave][idioma] = traducao_referencia
                texto_feedback_dialogo.value = f"você disse '{resposta_do_usuario}' — a tradução mais comum é '{traducao_referencia}', salvei essa"
                texto_feedback_dialogo.color = cor("erro")
                campo_resposta.value = traducao_referencia
                campo_resposta.border_color = cor("erro")
            else:
                vocabulario[chave][idioma] = resposta_do_usuario
                texto_feedback_dialogo.value = "palavra cadastrada no vocabulário!"
                texto_feedback_dialogo.color = cor("destaque")
                campo_resposta.border_color = cor("acerto")

            salvar_vocabulario_no_arquivo(estado["musica_selecionada"]["caminho_do_json"], vocabulario)
            atualizar_letra_na_tela()
        else:
            avaliacao = avaliar_resposta(campo_resposta.value, entrada[idioma])
            estado["tentativas"] += 1

            if avaliacao["status"] == "certo":
                estado["acertos"] += 1
                texto_feedback_dialogo.value = "isso aí!"
                texto_feedback_dialogo.color = cor("acerto")
                campo_resposta.border_color = cor("acerto")
            elif avaliacao["status"] == "quase":
                texto_feedback_dialogo.value = f"quase — resposta: {entrada[idioma]}"
                texto_feedback_dialogo.color = cor("erro")
                campo_resposta.value = entrada[idioma]
                campo_resposta.border_color = cor("erro")
            else:
                texto_feedback_dialogo.value = f"era: {entrada[idioma]}"
                texto_feedback_dialogo.color = cor("erro")
                campo_resposta.value = entrada[idioma]
                campo_resposta.border_color = cor("erro")

            texto_placar.value = f"acertos: {estado['acertos']} / {estado['tentativas']}"

        pagina.update()

    async def revelar_resposta(e):
        vocabulario = estado["musica_selecionada"]["vocabulario"]
        chave = estado_dialogo["chave_palavra"]
        entrada = vocabulario.get(chave)
        idioma = estado["idioma_de_estudo"]

        traducao = entrada.get(idioma) if entrada else None

        if not traducao:
            texto_feedback_dialogo.value = "buscando..."
            texto_feedback_dialogo.color = cor("texto_secundario")
            pagina.update()

            traducao = await asyncio.to_thread(tentar_traduzir, chave, idioma)
            if traducao:
                vocabulario[chave] = vocabulario.get(chave, {"pt": "", "en": ""})
                vocabulario[chave][idioma] = traducao
                salvar_vocabulario_no_arquivo(estado["musica_selecionada"]["caminho_do_json"], vocabulario)
                atualizar_letra_na_tela()

        if not traducao:
            texto_feedback_dialogo.value = "não consegui encontrar a tradução dessa palavra."
            texto_feedback_dialogo.color = cor("erro")
            pagina.update()
            return

        estado["tentativas"] += 1
        texto_placar.value = f"acertos: {estado['acertos']} / {estado['tentativas']}"
        texto_feedback_dialogo.value = f"era: {traducao}"
        texto_feedback_dialogo.color = cor("erro")
        campo_resposta.value = traducao
        campo_resposta.border_color = cor("erro")
        pagina.update()

    def fechar_dialogo(e=None):
        pagina.pop_dialog()
        pagina.update()

    campo_resposta.on_submit = conferir_resposta

    botao_fechar_dialogo_palavra = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED, icon_size=18, icon_color=cor("texto_secundario"), on_click=fechar_dialogo,
    )

    dialogo_palavra = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[texto_palavra_dialogo, botao_fechar_dialogo_palavra],
        ),
        content=ft.Column(
            tight=True,
            spacing=10,
            controls=[
                ft.Text("qual é a tradução dessa palavra?", size=15, font_family=FONTE_CORPO, color=cor("texto_secundario")),
                campo_resposta,
                texto_feedback_dialogo,
            ],
        ),
        actions=[
            ft.TextButton("não sei", on_click=revelar_resposta, style=ft.ButtonStyle(color=cor("erro"))),
            ft.Button("conferir", on_click=conferir_resposta, bgcolor=cor("destaque"), color="white"),
        ],
    )

    def montar_linha_modo_ouvir(indice: int, linha: dict):
        eh_linha_atual = indice == estado["indice_linha_atual"]
        eh_linha_selecionada = indice == estado["linha_selecionada"]

        return ft.Container(
            key=str(indice),
            content=ft.Text(
                linha["fr"],
                size=21 if eh_linha_atual else 18,
                weight=ft.FontWeight.BOLD if eh_linha_atual else ft.FontWeight.NORMAL,
                color=cor("destaque") if eh_linha_atual else cor("texto_principal"),
            ),
            padding=ft.Padding.symmetric(vertical=8, horizontal=14),
            bgcolor=cor("cartao_claro") if eh_linha_selecionada else None,
            on_click=lambda e, indice=indice, linha=linha: pagina.run_task(ao_clicar_linha, indice, linha),
            ink=True,
            animate=200,
        )

    def montar_linha_modo_estudar(indice: int, linha: dict):
        eh_linha_atual = indice == estado["indice_linha_atual"]
        palavras = dividir_linha_em_palavras(linha["fr"])
        vocabulario = estado["musica_selecionada"]["vocabulario"]

        chips_das_palavras = []
        for palavra in palavras:
            chave = normalizar_chave_de_palavra(palavra)

            if chave.isdigit():
                chips_das_palavras.append(
                    ft.Container(
                        content=ft.Text(palavra, size=18, font_family=FONTE_CORPO, color=cor("texto_secundario")),
                        padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                    )
                )
                continue

            entrada = vocabulario.get(chave)
            eh_traduzida = bool(entrada and entrada.get(estado["idioma_de_estudo"]))

            chips_das_palavras.append(
                ft.Container(
                    content=ft.Text(
                        palavra,
                        size=18,
                        font_family=FONTE_CORPO,
                        color="white" if eh_traduzida else cor("texto_principal"),
                        weight=ft.FontWeight.W_600 if eh_traduzida else None,
                    ),
                    padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                    border_radius=8,
                    bgcolor=cor("destaque") if eh_traduzida else cor("palavra_clicavel"),
                    on_click=lambda e, p=palavra: abrir_dialogo_da_palavra(p),
                    ink=True,
                )
            )

        return ft.Container(
            content=ft.Row(controls=chips_das_palavras, wrap=True, spacing=6, run_spacing=6),
            padding=ft.Padding.symmetric(vertical=6, horizontal=10),
            border_radius=10,
            bgcolor=cor("cartao_claro") if eh_linha_atual else None,
            animate=200,
        )

    def atualizar_letra_na_tela():
        if estado["musica_selecionada"] is None:
            return

        linhas = estado["musica_selecionada"]["linhas"]

        if estado["modo"] == MODO_OUVIR:
            coluna_letra_ouvir.controls.clear()
            centro = estado["indice_linha_atual"] if estado["indice_linha_atual"] >= 0 else 0
            janela = 3
            inicio = max(0, centro - janela)
            fim = min(len(linhas), centro + janela + 1)
            for indice in range(inicio, fim):
                coluna_letra_ouvir.controls.append(montar_linha_modo_ouvir(indice, linhas[indice]))
        elif estado["modo"] == MODO_ESTUDAR:
            coluna_letra.controls.clear()
            for indice, linha in enumerate(linhas):
                coluna_letra.controls.append(montar_linha_modo_estudar(indice, linha))

    def montar_vocabulario_global() -> dict:
        vocabulario_global = {}
        for musica in lista_de_musicas:
            for chave, entrada in musica.get("vocabulario", {}).items():
                if chave.isdigit():
                    continue
                if chave not in vocabulario_global:
                    vocabulario_global[chave] = {"pt": "", "en": "", "musica": musica["titulo"]}
                for idioma in ("pt", "en"):
                    if entrada.get(idioma) and not vocabulario_global[chave].get(idioma):
                        vocabulario_global[chave][idioma] = entrada[idioma]
        return vocabulario_global

    def atualizar_lista_de_palavras_aprendidas():
        if estado["modo"] != MODO_REVISAR:
            return

        idioma = estado["idioma_de_estudo"]
        filtro = normalizar_para_comparar(estado["filtro_palavras"])
        vocabulario_global = montar_vocabulario_global()
        palavras_aprendidas = sorted(
            (chave, entrada) for chave, entrada in vocabulario_global.items()
            if entrada.get(idioma)
            and (
                not filtro
                or filtro in normalizar_para_comparar(chave)
                or filtro in normalizar_para_comparar(entrada[idioma])
            )
        )

        coluna_palavras_aprendidas.controls.clear()

        if not palavras_aprendidas:
            mensagem = (
                "nenhuma palavra encontrada."
                if filtro
                else "nenhuma palavra aprendida ainda — estude no modo 'estudar palavras' primeiro."
            )
            coluna_palavras_aprendidas.controls.append(
                ft.Text(mensagem, color=cor("texto_secundario"), font_family=FONTE_CORPO, size=17, italic=True)
            )
            return

        for chave, entrada in palavras_aprendidas:
            coluna_palavras_aprendidas.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                    border=ft.Border.all(1, cor("cartao_claro")),
                    bgcolor=cor("palavra_clicavel"),
                    content=ft.Row(
                        controls=[
                            ft.Text(chave, size=19, font_family=FONTE_CORPO, weight=ft.FontWeight.BOLD, color=cor("texto_principal"), width=180),
                            ft.Text(entrada[idioma], size=19, font_family=FONTE_CORPO, color=cor("destaque"), expand=True),
                            ft.Text(entrada["musica"], size=13, font_family=FONTE_CORPO, color=cor("texto_secundario"), no_wrap=True),
                        ],
                    ),
                )
            )

    def extrair_capa_do_mp3(caminho_absoluto: str) -> bytes | None:
        try:
            apics = ID3(caminho_absoluto).getall("APIC")
            return apics[0].data if apics else None
        except Exception:
            return None

    def icone_capa_padrao(tamanho: int) -> ft.Icon:
        return ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color=cor("destaque"), size=tamanho)

    async def selecionar_musica(musica: dict):
        estado["musica_selecionada"] = musica
        estado["indice_linha_atual"] = -1
        estado["linha_selecionada"] = None
        estado["acertos"] = 0
        estado["tentativas"] = 0
        estado["indice_ditado"] = None
        estado["fim_trecho_ditado"] = None
        estado["questoes_ditado"] = 0
        estado["exercicio_traducao"] = None
        texto_placar.value = "acertos: 0 / 0"

        titulo_musica_texto.value = musica["titulo"]
        artista_musica_texto.value = musica["artista"]
        titulo_mini_texto.value = musica["titulo"]
        artista_mini_texto.value = musica["artista"]
        botao_favoritar_player.icon = ft.Icons.FAVORITE_ROUNDED if musica["favorito"] else ft.Icons.FAVORITE_BORDER_ROUNDED
        botao_favoritar_player.icon_color = cor("destaque") if musica["favorito"] else cor("texto_secundario")
        redesenhar_lista_de_musicas()

        pygame.mixer.music.stop()
        caminho_audio_absoluto = musica.get("caminho_audio_absoluto")

        capa = extrair_capa_do_mp3(caminho_audio_absoluto) if caminho_audio_absoluto else None
        if capa:
            capa_musica_cabecalho.content = ft.Image(src=capa, width=76, height=76, fit=ft.BoxFit.COVER)
            capa_mini.content = ft.Image(src=capa, width=44, height=44, fit=ft.BoxFit.COVER)
        else:
            capa_musica_cabecalho.content = icone_capa_padrao(32)
            capa_mini.content = icone_capa_padrao(22)

        if caminho_audio_absoluto:
            pygame.mixer.music.load(caminho_audio_absoluto)
            try:
                estado["duracao_audio"] = MP3(caminho_audio_absoluto).info.length
            except Exception:
                estado["duracao_audio"] = 0.0
        else:
            estado["duracao_audio"] = 0.0

        slider_progresso.max = estado["duracao_audio"] or 100
        texto_tempo_total.value = formatar_tempo(estado["duracao_audio"])
        texto_tempo_atual.value = "00:00"
        slider_progresso.value = 0

        estado["tocando"] = False
        estado["reproducao_iniciada"] = False
        estado["offset_pygame"] = 0.0
        botao_play_pause.icon = ft.Icons.PLAY_ARROW_ROUNDED

        painel_traducao.content = ft.Text(
            "clique em uma linha da letra para ver a tradução aqui.",
            color=cor("texto_secundario"),
            size=18,
            font_family=FONTE_CORPO,
            italic=True,
        )

        atualizar_letra_na_tela()
        if estado["modo"] == MODO_DITADO:
            preparar_ditado()
        elif estado["modo"] == MODO_TRADUZIR:
            preparar_traducao()
        pagina.update()

    def escolher_proxima_musica():
        if not lista_de_musicas or estado["musica_selecionada"] is None:
            return None

        if estado["aleatorio"]:
            candidatas = [
                m for m in lista_de_musicas
                if m["caminho_do_json"] != estado["musica_selecionada"]["caminho_do_json"]
            ]
            return random.choice(candidatas) if candidatas else lista_de_musicas[0]

        indice_atual = next(
            (i for i, m in enumerate(lista_de_musicas) if m["caminho_do_json"] == estado["musica_selecionada"]["caminho_do_json"]),
            -1,
        )
        return lista_de_musicas[(indice_atual + 1) % len(lista_de_musicas)]

    def escolher_musica_anterior():
        if not lista_de_musicas or estado["musica_selecionada"] is None:
            return None

        indice_atual = next(
            (i for i, m in enumerate(lista_de_musicas) if m["caminho_do_json"] == estado["musica_selecionada"]["caminho_do_json"]),
            -1,
        )
        return lista_de_musicas[(indice_atual - 1) % len(lista_de_musicas)]

    async def ao_clicar_proximo(e):
        proxima = escolher_proxima_musica()
        if proxima:
            await selecionar_musica(proxima)

    async def ao_clicar_anterior(e):
        anterior = escolher_musica_anterior()
        if anterior:
            await selecionar_musica(anterior)

    def ao_clicar_aleatorio(e):
        estado["aleatorio"] = not estado["aleatorio"]
        botao_aleatorio.icon_color = cor("destaque") if estado["aleatorio"] else cor("texto_secundario")
        botao_aleatorio.tooltip = "desativar modo aleatório" if estado["aleatorio"] else "ativar modo aleatório e trocar de música"
        pagina.update()
        if estado["aleatorio"]:
            pagina.run_task(ao_clicar_proximo, None)

    def tem_audio_carregado() -> bool:
        return bool(
            estado["musica_selecionada"] and estado["musica_selecionada"].get("caminho_audio_absoluto")
        )

    async def ao_clicar_play_pause(e):
        if not tem_audio_carregado():
            return

        if estado["tocando"]:
            pygame.mixer.music.pause()
            botao_play_pause.icon = ft.Icons.PLAY_ARROW_ROUNDED
        else:
            if estado["reproducao_iniciada"]:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.play(start=estado["offset_pygame"])
                estado["reproducao_iniciada"] = True
            botao_play_pause.icon = ft.Icons.PAUSE_ROUNDED
        estado["tocando"] = not estado["tocando"]
        pagina.update()

    async def atualizar_posicao(posicao_segundos: float):
        texto_tempo_atual.value = formatar_tempo(posicao_segundos)
        slider_progresso.value = min(posicao_segundos, slider_progresso.max)

        if estado["musica_selecionada"] is None:
            return

        linhas = estado["musica_selecionada"]["linhas"]
        novo_indice = encontrar_indice_da_linha_atual(linhas, posicao_segundos)

        if novo_indice != estado["indice_linha_atual"]:
            estado["indice_linha_atual"] = novo_indice
            atualizar_letra_na_tela()

            if estado["modo"] == MODO_OUVIR and switch_seguir_letra.value:
                mostrar_traducao_da_linha(novo_indice)

            pagina.update()

    async def buscar_posicao(segundos: float):
        if not tem_audio_carregado():
            return

        estado["offset_pygame"] = segundos
        pygame.mixer.music.play(start=segundos)
        estado["reproducao_iniciada"] = True
        estado["tocando"] = True
        botao_play_pause.icon = ft.Icons.PAUSE_ROUNDED
        await atualizar_posicao(segundos)
        pagina.update()

    async def ao_arrastar_slider(e):
        await buscar_posicao(float(e.control.value))

    async def ao_clicar_linha(indice: int, linha: dict):
        await buscar_posicao(linha["tempo"])
        mostrar_traducao_da_linha(indice)

    def obter_linha_ditado():
        musica = estado["musica_selecionada"]
        indice = estado["indice_ditado"]
        if not musica or indice is None or indice >= len(musica["linhas"]):
            return None
        return musica["linhas"][indice]

    async def tocar_trecho_ditado(e=None):
        linha = obter_linha_ditado()
        musica = estado["musica_selecionada"]
        if not linha or not musica or not tem_audio_carregado():
            texto_feedback_ditado.value = "selecione o arquivo de áudio para praticar."
            pagina.update()
            return

        estado["fim_trecho_ditado"] = fim_do_trecho(
            musica["linhas"], estado["indice_ditado"], estado["duracao_audio"]
        )
        await buscar_posicao(float(linha["tempo"]))

    def preparar_ditado(e=None):
        musica = estado["musica_selecionada"]
        if not musica:
            texto_ditado_instrucao.value = "escolha uma música para começar."
            return

        validos = indices_validos_para_ditado(musica["linhas"])
        if not validos:
            texto_ditado_instrucao.value = "essa música não tem trechos adequados para ditado."
            campo_ditado.disabled = True
            return

        anterior = estado["indice_ditado"]
        opcoes = [indice for indice in validos if indice != anterior] or validos
        estado["indice_ditado"] = random.choice(opcoes)
        estado["fim_trecho_ditado"] = None
        estado["questoes_ditado"] += 1
        texto_ditado_etapa.value = f"trecho {estado['questoes_ditado']}"
        progresso_ditado.value = min((estado["questoes_ditado"] - 1) % 10 / 10, 1)
        texto_ditado_instrucao.value = "ouça o trecho e escreva exatamente o que entendeu em francês"
        campo_ditado.value = ""
        campo_ditado.disabled = False
        texto_feedback_ditado.value = ""
        texto_resposta_ditado.value = ""
        botao_conferir_ditado.visible = True
        botao_revelar_ditado.visible = True
        botao_pular_ditado.visible = True
        botao_proximo_ditado.visible = False
        pagina.update()
        pagina.run_task(tocar_trecho_ditado)

    def finalizar_pergunta_ditado():
        campo_ditado.disabled = True
        botao_conferir_ditado.visible = False
        botao_revelar_ditado.visible = False
        botao_pular_ditado.visible = False
        botao_proximo_ditado.visible = True

    def conferir_ditado(e=None):
        linha = obter_linha_ditado()
        if not linha:
            return
        resultado = avaliar_resposta(campo_ditado.value, linha["fr"])
        if resultado["status"] == "vazio":
            texto_feedback_ditado.value = "digite o que você ouviu primeiro."
            texto_feedback_ditado.color = cor("erro")
            pagina.update()
            return

        if resultado["status"] == "certo":
            texto_feedback_ditado.value = "certo! você ouviu muito bem. 🌸"
            texto_feedback_ditado.color = cor("acerto")
        elif resultado["status"] == "quase":
            detalhes = []
            if resultado["faltaram"]:
                detalhes.append("faltou: " + ", ".join(resultado["faltaram"]))
            if resultado["sobraram"]:
                detalhes.append("a mais: " + ", ".join(resultado["sobraram"]))
            texto_feedback_ditado.value = "quase! " + " • ".join(detalhes)
            texto_feedback_ditado.color = cor("erro")
        else:
            texto_feedback_ditado.value = "ainda não. compare sua resposta com a letra."
            texto_feedback_ditado.color = cor("erro")

        traducao = linha.get(estado["idioma_de_estudo"], "")
        texto_resposta_ditado.value = f"resposta: {linha['fr']}\ntradução: {traducao}"
        finalizar_pergunta_ditado()
        pagina.update()

    def revelar_ditado(e=None):
        linha = obter_linha_ditado()
        if not linha:
            return
        texto_feedback_ditado.value = "sem problema — ouça de novo acompanhando a resposta."
        texto_feedback_ditado.color = cor("texto_secundario")
        traducao = linha.get(estado["idioma_de_estudo"], "")
        texto_resposta_ditado.value = f"resposta: {linha['fr']}\ntradução: {traducao}"
        finalizar_pergunta_ditado()
        pagina.update()
        pagina.run_task(tocar_trecho_ditado)

    campo_ditado.on_submit = conferir_ditado
    botao_ouvir_ditado.on_click = tocar_trecho_ditado
    botao_repetir_ditado.on_click = tocar_trecho_ditado
    botao_conferir_ditado.on_click = conferir_ditado
    botao_revelar_ditado.on_click = revelar_ditado
    botao_pular_ditado.on_click = preparar_ditado
    botao_proximo_ditado.on_click = preparar_ditado

    def preparar_traducao(e=None):
        musica = estado["musica_selecionada"]
        linhas = musica["linhas"] if musica else []
        exercicios = exercicios_ingles_para_frances(linhas)
        anterior = estado["exercicio_traducao"]
        opcoes = [item for item in exercicios if item != anterior] or exercicios
        if not opcoes:
            texto_frase_ingles.value = "No exercises available"
            campo_traducao_frances.disabled = True
            pagina.update()
            return

        estado["exercicio_traducao"] = random.choice(opcoes)
        exercicio = estado["exercicio_traducao"]
        texto_frase_ingles.value = exercicio["en"]
        texto_origem_traducao.value = exercicio["origem"]
        campo_traducao_frances.value = ""
        campo_traducao_frances.disabled = False
        texto_feedback_traducao.value = ""
        texto_gabarito_traducao.value = ""
        botao_revelar_traducao.visible = True
        botao_tentar_novamente_traducao.visible = False
        botao_pular_traducao.visible = True
        botao_conferir_traducao.visible = True
        botao_proxima_traducao.visible = False
        pagina.update()

    def finalizar_traducao():
        campo_traducao_frances.disabled = True
        botao_revelar_traducao.visible = False
        botao_pular_traducao.visible = False
        botao_conferir_traducao.visible = False
        botao_proxima_traducao.visible = True

    def conferir_traducao(e=None):
        exercicio = estado["exercicio_traducao"]
        if not exercicio:
            return
        resultado = avaliar_resposta(campo_traducao_frances.value, exercicio["fr"])
        if resultado["status"] == "vazio":
            texto_feedback_traducao.value = "escreva uma tradução primeiro."
            texto_feedback_traducao.color = cor("erro")
            pagina.update()
            return

        if resultado["status"] == "certo":
            texto_feedback_traducao.value = "certo! 🌸"
            texto_feedback_traducao.color = cor("acerto")
        elif resultado["status"] == "quase":
            detalhes = []
            if resultado["faltaram"]:
                detalhes.append("faltou: " + ", ".join(resultado["faltaram"]))
            if resultado["sobraram"]:
                detalhes.append("a mais: " + ", ".join(resultado["sobraram"]))
            texto_feedback_traducao.value = "quase, mas ainda está errado. " + " • ".join(detalhes)
            texto_feedback_traducao.color = cor("erro")
        else:
            texto_feedback_traducao.value = "errado. compare com a resposta correta."
            texto_feedback_traducao.color = cor("erro")

        texto_gabarito_traducao.value = f"resposta: {exercicio['fr']}"
        finalizar_traducao()
        pagina.update()

    def revelar_traducao(e=None):
        exercicio = estado["exercicio_traducao"]
        if not exercicio:
            return
        texto_feedback_traducao.value = "resposta mostrada."
        texto_feedback_traducao.color = cor("texto_secundario")
        texto_gabarito_traducao.value = f"resposta: {exercicio['fr']}"
        finalizar_traducao()
        botao_tentar_novamente_traducao.visible = True
        pagina.update()

    def tentar_novamente_traducao(e=None):
        campo_traducao_frances.value = ""
        campo_traducao_frances.disabled = False
        texto_feedback_traducao.value = ""
        texto_gabarito_traducao.value = ""
        botao_revelar_traducao.visible = True
        botao_tentar_novamente_traducao.visible = False
        botao_pular_traducao.visible = True
        botao_conferir_traducao.visible = True
        botao_proxima_traducao.visible = False
        pagina.update()

    campo_traducao_frances.on_submit = conferir_traducao
    botao_conferir_traducao.on_click = conferir_traducao
    botao_revelar_traducao.on_click = revelar_traducao
    botao_tentar_novamente_traducao.on_click = tentar_novamente_traducao
    botao_pular_traducao.on_click = preparar_traducao
    botao_proxima_traducao.on_click = preparar_traducao

    async def acompanhar_posicao_em_loop():
        while True:
            await asyncio.sleep(0.4)
            try:
                if not estado["tocando"]:
                    continue

                if not pygame.mixer.music.get_busy():
                    estado["tocando"] = False
                    estado["reproducao_iniciada"] = False
                    estado["offset_pygame"] = 0.0
                    botao_play_pause.icon = ft.Icons.PLAY_ARROW_ROUNDED

                    proxima = escolher_proxima_musica()
                    if proxima:
                        await selecionar_musica(proxima)
                        await ao_clicar_play_pause(None)
                    pagina.update()
                    continue

                posicao_segundos = estado["offset_pygame"] + pygame.mixer.music.get_pos() / 1000
                if (
                    estado["modo"] == MODO_DITADO
                    and estado["fim_trecho_ditado"] is not None
                    and posicao_segundos >= estado["fim_trecho_ditado"]
                ):
                    pygame.mixer.music.stop()
                    estado["tocando"] = False
                    estado["reproducao_iniciada"] = False
                    estado["fim_trecho_ditado"] = None
                    botao_play_pause.icon = ft.Icons.PLAY_ARROW_ROUNDED
                    pagina.update()
                    continue
                await atualizar_posicao(posicao_segundos)
                pagina.update()
            except Exception as erro:
                print(f"acompanhar_posicao_em_loop: erro ignorado nesse tick: {erro!r}", flush=True)

    botao_play_pause.on_click = ao_clicar_play_pause
    botao_proximo.on_click = ao_clicar_proximo
    botao_anterior.on_click = ao_clicar_anterior
    botao_aleatorio.on_click = ao_clicar_aleatorio
    slider_progresso.on_change_end = ao_arrastar_slider
    pagina.run_task(acompanhar_posicao_em_loop)

    campo_url_spotdl = ft.TextField(
        hint_text="link do spotify",
        text_size=12,
        dense=True,
        border_radius=8,
        bgcolor=cor("cartao"),
        expand=True,
    )

    texto_status_download = ft.Text("", size=11, color=cor("texto_secundario"))
    progresso_download = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

    def ao_favoritar(musica: dict):
        musica["favorito"] = not musica["favorito"]
        salvar_metadados_no_arquivo(musica["caminho_do_json"], favorito=musica["favorito"])
        redesenhar_lista_de_musicas()
        if estado["musica_selecionada"] and estado["musica_selecionada"]["caminho_do_json"] == musica["caminho_do_json"]:
            botao_favoritar_player.icon = ft.Icons.FAVORITE_ROUNDED if musica["favorito"] else ft.Icons.FAVORITE_BORDER_ROUNDED
            botao_favoritar_player.icon_color = cor("destaque") if musica["favorito"] else cor("texto_secundario")
        pagina.update()

    estado_menu_musica = {"atual": None}

    def fechar_menu_contexto():
        menu_contexto_musica.visible = False
        capturador_fechar_menu.visible = False
        pagina.update()

    def favoritar_do_menu(ev):
        musica = estado_menu_musica["atual"]
        fechar_menu_contexto()
        if musica:
            ao_favoritar(musica)

    def excluir_do_menu(ev):
        musica = estado_menu_musica["atual"]
        fechar_menu_contexto()
        if musica:
            pagina.run_task(confirmar_exclusao_musica, musica)

    texto_titulo_menu = ft.Text(
        "", size=13, font_family=FONTE_CORPO, color=cor("texto_secundario"),
        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
    )
    icone_favoritar_menu = ft.Icon(ft.Icons.FAVORITE_BORDER_ROUNDED, size=17, color=cor("destaque"))
    texto_favoritar_menu = ft.Text("favoritar", size=14, font_family=FONTE_CORPO, color=cor("destaque"))
    icone_excluir_menu = ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED, size=17, color=cor("erro"))
    texto_excluir_menu = ft.Text("excluir música", size=14, font_family=FONTE_CORPO, color=cor("erro"))

    capturador_fechar_menu = ft.GestureDetector(
        visible=False, expand=True,
        on_tap=lambda e: fechar_menu_contexto(),
        on_secondary_tap=lambda e: fechar_menu_contexto(),
    )

    menu_contexto_musica = ft.Container(
        visible=False,
        width=220,
        border_radius=14,
        bgcolor=cor("cartao"),
        padding=ft.Padding.symmetric(horizontal=6, vertical=8),
        shadow=ft.BoxShadow(blur_radius=20, spread_radius=-2, offset=ft.Offset(0, 6), color=cor("sombra")),
        content=ft.Column(
            tight=True, spacing=2,
            controls=[
                ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=4), content=texto_titulo_menu),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=9), border_radius=10, ink=True,
                    on_click=favoritar_do_menu,
                    content=ft.Row(spacing=10, controls=[icone_favoritar_menu, texto_favoritar_menu]),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=9), border_radius=10, ink=True,
                    on_click=excluir_do_menu,
                    content=ft.Row(spacing=10, controls=[icone_excluir_menu, texto_excluir_menu]),
                ),
            ],
        ),
    )

    def mostrar_menu_contexto_musica(e, musica: dict):
        estado_menu_musica["atual"] = musica
        texto_titulo_menu.value = musica["titulo"]
        icone_favoritar_menu.name = ft.Icons.FAVORITE_ROUNDED if musica["favorito"] else ft.Icons.FAVORITE_BORDER_ROUNDED
        texto_favoritar_menu.value = "remover dos favoritos" if musica["favorito"] else "favoritar"

        largura_janela = pagina.window.width or 1100
        altura_janela = pagina.window.height or 780
        largura_menu, altura_menu = 220, 130

        x = e.global_position.x if getattr(e, "global_position", None) else 320
        y = e.global_position.y if getattr(e, "global_position", None) else 100

        menu_contexto_musica.left = max(8, min(x + 8, largura_janela - largura_menu - 10))
        menu_contexto_musica.top = max(8, min(y, altura_janela - altura_menu - 10))
        menu_contexto_musica.visible = True
        capturador_fechar_menu.visible = True
        pagina.update()

    async def confirmar_exclusao_musica(musica: dict):
        def excluir(e):
            pagina.pop_dialog()
            shutil.rmtree(musica["pasta"], ignore_errors=True)
            if (
                estado["musica_selecionada"]
                and estado["musica_selecionada"]["caminho_do_json"] == musica["caminho_do_json"]
            ):
                pygame.mixer.music.stop()
                estado["musica_selecionada"] = None
                estado["tocando"] = False
                estado["reproducao_iniciada"] = False
                titulo_musica_texto.value = "selecione uma música"
                artista_musica_texto.value = ""
                titulo_mini_texto.value = "selecione uma música"
                artista_mini_texto.value = ""
                coluna_letra.controls.clear()
                coluna_letra_ouvir.controls.clear()
            atualizar_lista_de_musicas_ui()
            pagina.update()

        def cancelar(e):
            pagina.pop_dialog()
            pagina.update()

        pagina.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("excluir música?", font_family=FONTE_CORPO, color=cor("texto_principal")),
                content=ft.Text(
                    f"isso apaga o áudio e a letra de '{musica['titulo']}' pra sempre.",
                    font_family=FONTE_CORPO, color=cor("texto_secundario"),
                ),
                actions=[
                    ft.TextButton("cancelar", on_click=cancelar),
                    ft.Button("excluir", on_click=excluir, bgcolor=cor("erro"), color="white"),
                ],
            )
        )
        pagina.update()

    def criar_item_de_musica(musica: dict):
        eh_atual = (
            estado["musica_selecionada"] is not None
            and estado["musica_selecionada"]["caminho_do_json"] == musica["caminho_do_json"]
        )
        tem_audio = bool(musica.get("caminho_audio"))

        corpo = ft.Container(
            padding=ft.Padding.symmetric(horizontal=6, vertical=8),
            border_radius=16,
            bgcolor=cor("cartao_claro") if eh_atual else None,
            ink=True,
            content=ft.Row(
                spacing=6,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.FAVORITE_ROUNDED if musica["favorito"] else ft.Icons.FAVORITE_BORDER_ROUNDED,
                        icon_color=cor("destaque") if musica["favorito"] else cor("texto_secundario"),
                        icon_size=16,
                        on_click=lambda e, m=musica: ao_favoritar(m),
                    ),
                    ft.Icon(
                        ft.Icons.GRAPHIC_EQ_ROUNDED if eh_atual else ft.Icons.MUSIC_NOTE_ROUNDED,
                        color=cor("destaque") if eh_atual else cor("texto_secundario"),
                        size=18,
                    ),
                    ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            ft.Text(
                                musica["titulo"],
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=cor("destaque") if eh_atual else cor("texto_principal"),
                                no_wrap=True,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(musica["artista"], color=cor("texto_secundario"), size=11, no_wrap=True),
                        ],
                    ),
                    *([] if tem_audio else [ft.Icon(ft.Icons.MUSIC_OFF_ROUNDED, color=cor("texto_secundario"), size=14)]),
                ],
            ),
        )

        return ft.GestureDetector(
            key=musica["caminho_do_json"],
            on_tap=lambda e, m=musica: pagina.run_task(selecionar_musica, m),
            on_secondary_tap_down=lambda e, m=musica: mostrar_menu_contexto_musica(e, m),
            content=corpo,
        )

    def obter_musicas_exibidas() -> list[dict]:
        filtro = normalizar_para_comparar(estado["filtro_busca"])
        musicas_filtradas = [
            musica for musica in lista_de_musicas
            if not filtro
            or filtro in normalizar_para_comparar(musica["titulo"])
            or filtro in normalizar_para_comparar(musica["artista"])
        ]

        if estado["ordenar_alfabeticamente"]:
            musicas_filtradas.sort(key=lambda m: normalizar_para_comparar(m["titulo"]))
        else:
            musicas_filtradas.sort(key=lambda m: (not m["favorito"], m["ordem"]))

        return musicas_filtradas

    def redesenhar_lista_de_musicas():
        musicas_exibidas = obter_musicas_exibidas()
        coluna_musicas.controls = [criar_item_de_musica(musica) for musica in musicas_exibidas]

        if not musicas_exibidas:
            coluna_musicas.controls.append(
                ft.Container(
                    key="vazio",
                    content=ft.Text("nenhuma música encontrada", size=15, font_family=FONTE_CORPO, color=cor("texto_secundario"), italic=True),
                )
            )

    def ao_reordenar_musicas(e: ft.OnReorderEvent):
        if estado["filtro_busca"] or estado["ordenar_alfabeticamente"]:
            return

        musicas_exibidas = obter_musicas_exibidas()
        if e.old_index >= len(musicas_exibidas) or e.new_index >= len(musicas_exibidas):
            return

        musica_movida = musicas_exibidas.pop(e.old_index)
        musicas_exibidas.insert(e.new_index, musica_movida)

        for indice, musica in enumerate(musicas_exibidas):
            musica["ordem"] = indice
            salvar_metadados_no_arquivo(musica["caminho_do_json"], ordem=indice)

        redesenhar_lista_de_musicas()
        pagina.update()

    def atualizar_lista_de_musicas_ui():
        nonlocal lista_de_musicas
        lista_de_musicas = carregar_lista_de_musicas()
        redesenhar_lista_de_musicas()
        pagina.update()

    def criar_letra_json_se_necessario(pasta_da_musica: Path) -> bool:
        caminho_json = pasta_da_musica / "letra.json"
        if caminho_json.exists():
            return True

        titulo, artista = extrair_titulo_e_artista(pasta_da_musica.name)
        texto_lrc = buscar_letra_sincronizada(titulo, artista)

        if not texto_lrc:
            return False

        linhas = analisar_texto_lrc(texto_lrc)
        for linha in linhas:
            linha["pt"] = tentar_traduzir(linha["fr"], "pt")
            linha["en"] = tentar_traduzir(linha["fr"], "en")
        vocabulario = montar_vocabulario(linhas, traduzir_automaticamente=True)

        dados_da_musica = {
            "titulo": titulo,
            "artista": artista,
            "arquivo_audio": "audio.mp3",
            "linhas": linhas,
            "vocabulario": vocabulario,
        }
        with open(caminho_json, "w", encoding="utf-8") as arquivo:
            json.dump(dados_da_musica, arquivo, ensure_ascii=False, indent=2)
        return True

    def executar_download(url: str):
        pasta_destino = Path("musicas")
        pasta_destino.mkdir(exist_ok=True)

        pastas_antes = {p.name for p in pasta_destino.iterdir() if p.is_dir()}

        comando = [
            "spotdl", url,
            "--output", str(pasta_destino / "{artist} - {title}" / "audio"),
            "--format", "mp3",
        ]

        try:
            resultado = subprocess.run(comando, capture_output=True, text=True)
            if resultado.returncode == 0:
                pastas_depois = {p.name for p in pasta_destino.iterdir() if p.is_dir()}
                pastas_novas = pastas_depois - pastas_antes

                sucesso = 0
                falhas = 0
                for nome_da_pasta in pastas_novas:
                    pasta = pasta_destino / nome_da_pasta
                    if criar_letra_json_se_necessario(pasta):
                        sucesso += 1
                    else:
                        falhas += 1
                        shutil.rmtree(pasta, ignore_errors=True)

                partes_mensagem = []
                if sucesso:
                    partes_mensagem.append(f"{sucesso} música(s) baixada(s) e traduzida(s)!")
                if falhas:
                    partes_mensagem.append(f"{falhas} sem letra encontrada, removida(s).")
                texto_status_download.value = " ".join(partes_mensagem) if partes_mensagem else "download concluído!"
                texto_status_download.color = cor("acerto") if sucesso or not falhas else cor("erro")
                atualizar_lista_de_musicas_ui()
            else:
                texto_status_download.value = "erro no download."
                texto_status_download.color = cor("erro")
        except FileNotFoundError:
            texto_status_download.value = "spotdl não encontrado."
            texto_status_download.color = cor("erro")
        finally:
            progresso_download.visible = False
            botao_baixar.disabled = False
            pagina.update()

    def iniciar_download_spotdl(e):
        url = campo_url_spotdl.value.strip()
        if not url:
            return

        texto_status_download.value = "baixando..."
        texto_status_download.color = cor("destaque")
        progresso_download.visible = True
        botao_baixar.disabled = True
        campo_url_spotdl.value = ""
        pagina.update()

        threading.Thread(target=executar_download, args=(url,), daemon=True).start()

    botao_baixar = ft.IconButton(
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        icon_color=cor("destaque"),
        tooltip="baixar música, álbum ou playlist via spotdl",
        on_click=iniciar_download_spotdl,
    )

    secao_spotdl = criar_cartao(
        "baixar música",
        ft.Column([
            ft.Row([campo_url_spotdl, botao_baixar]),
            ft.Row([progresso_download, texto_status_download], spacing=8),
        ], spacing=6),
    )

    coluna_musicas = ft.ReorderableListView(
        expand=True, spacing=2, on_reorder=ao_reordenar_musicas, show_default_drag_handles=False,
    )

    def ao_digitar_busca(e):
        estado["filtro_busca"] = e.control.value
        redesenhar_lista_de_musicas()
        pagina.update()

    campo_busca = ft.TextField(
        hint_text="pesquisar música",
        text_size=15,
        dense=True,
        border_radius=30,
        border_color="transparent",
        filled=True,
        fill_color=cor("palavra_clicavel"),
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        on_change=ao_digitar_busca,
    )

    def ao_alternar_ordem_alfabetica(e):
        estado["ordenar_alfabeticamente"] = not estado["ordenar_alfabeticamente"]
        botao_ordem_alfabetica.icon_color = cor("destaque") if estado["ordenar_alfabeticamente"] else cor("texto_secundario")
        redesenhar_lista_de_musicas()
        pagina.update()

    botao_ordem_alfabetica = ft.IconButton(
        icon=ft.Icons.SORT_BY_ALPHA_ROUNDED,
        icon_color=cor("texto_secundario"),
        icon_size=18,
        tooltip="ordenar alfabeticamente",
        on_click=ao_alternar_ordem_alfabetica,
    )

    botao_tema = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE_ROUNDED if estado["escuro"] else ft.Icons.DARK_MODE_ROUNDED,
        icon_color=cor("texto_secundario"),
        icon_size=20,
        tooltip="alternar tema",
        on_click=lambda e: alternar_tema(e),
    )

    barra_lateral = ft.Container(
        width=300,
        bgcolor=cor("fundo_lateral"),
        padding=12,
        border=ft.Border.only(right=ft.BorderSide(1, cor("sombra"))),
        content=ft.Column(
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=6, top=2, bottom=10),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("˚₊· songlingo ·₊˚", size=20, font_family=FONTE_TITULO, weight=ft.FontWeight.W_600, color=cor("destaque")),
                            botao_tema,
                        ],
                    ),
                ),
                ft.Row(controls=[ft.Container(content=campo_busca, expand=True), botao_ordem_alfabetica], spacing=4),
                ft.Container(height=10),
                secao_spotdl,
                ft.Container(height=14),
                criar_cartao("minhas músicas", coluna_musicas, expandir=True),
            ],
            expand=True,
        ),
    )

    barra_agora_tocando = criar_cartao(
        "tocando agora",
        ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    width=280, spacing=8,
                    controls=[
                        capa_mini,
                        ft.Column([titulo_mini_texto, artista_mini_texto], spacing=0, expand=True),
                        botao_favoritar_player,
                        botao_excluir_player,
                    ],
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=4, alignment=ft.MainAxisAlignment.CENTER,
                            controls=[botao_aleatorio, botao_anterior, botao_play_pause, botao_proximo],
                        ),
                        ft.Row(spacing=6, controls=[texto_tempo_atual, slider_progresso, texto_tempo_total]),
                    ],
                ),
                ft.Row(
                    width=280, spacing=6, alignment=ft.MainAxisAlignment.END,
                    controls=[ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, color=cor("texto_secundario"), size=15), slider_volume],
                ),
            ],
        ),
        compacto=True,
    )

    janela_letra = criar_cartao(
        "letra", ft.Column(expand=True, controls=[coluna_letra, coluna_letra_ouvir]), expandir=True,
    )
    def ao_digitar_busca_palavras(e):
        estado["filtro_palavras"] = e.control.value
        atualizar_lista_de_palavras_aprendidas()
        pagina.update()

    campo_busca_palavras = ft.TextField(
        hint_text="pesquisar palavra aprendida",
        text_size=15,
        dense=True,
        border_radius=30,
        border_color="transparent",
        filled=True,
        fill_color=cor("palavra_clicavel"),
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        on_change=ao_digitar_busca_palavras,
    )

    janela_palavras_aprendidas = criar_cartao(
        "palavras aprendidas",
        ft.Column(expand=True, spacing=8, controls=[campo_busca_palavras, coluna_palavras_aprendidas]),
        expandir=True,
    )
    janela_palavras_aprendidas.visible = False

    cabecalho_musica = ft.Row(
        [capa_musica_cabecalho, ft.Column([titulo_musica_texto, artista_musica_texto], spacing=2)], spacing=16
    )
    linha_auxiliar_estudo = ft.Row([linha_seletor_de_idioma, ft.Container(expand=True), texto_placar])
    linha_switch_seguir = ft.Row([switch_seguir_letra])
    cartao_traducao = criar_cartao("tradução", painel_traducao)

    area_principal = ft.Container(
        expand=True,
        padding=25,
        content=ft.Column(
            expand=True,
            spacing=14,
            controls=[
                cabecalho_musica,
                linha_seletor_de_modo,
                linha_auxiliar_estudo,
                painel_defi.controle,
                janela_letra,
                painel_ditado,
                painel_traduzir,
                janela_palavras_aprendidas,
                linha_switch_seguir,
                cartao_traducao,
            ],
        ),
    )

    def aplicar_tema():
        pagina.theme_mode = ft.ThemeMode.DARK if estado["escuro"] else ft.ThemeMode.LIGHT
        pagina.bgcolor = cor("fundo")
        barra_lateral.bgcolor = cor("fundo_lateral")
        barra_lateral.border = ft.Border.only(right=ft.BorderSide(1, cor("sombra")))
        botao_tema.icon = ft.Icons.LIGHT_MODE_ROUNDED if estado["escuro"] else ft.Icons.DARK_MODE_ROUNDED
        botao_tema.icon_color = cor("texto_secundario")
        titulo_musica_texto.color = cor("texto_principal")
        artista_musica_texto.color = cor("texto_secundario")
        capa_musica_cabecalho.bgcolor = cor("cartao_claro")
        capa_musica_cabecalho.shadow = ft.BoxShadow(blur_radius=14, spread_radius=-4, offset=ft.Offset(0, 5), color=cor("sombra"))
        artista_mini_texto.color = cor("texto_secundario")
        capa_mini.bgcolor = cor("cartao_claro")
        texto_placar.color = cor("texto_secundario")
        slider_progresso.active_color = cor("destaque")
        texto_tempo_atual.color = cor("texto_secundario")
        texto_tempo_total.color = cor("texto_secundario")
        botao_play_pause.icon_color = cor("destaque")
        botao_anterior.icon_color = cor("texto_secundario")
        botao_proximo.icon_color = cor("texto_secundario")
        botao_excluir_player.icon_color = cor("texto_secundario")
        if estado["musica_selecionada"]:
            eh_favorita = estado["musica_selecionada"]["favorito"]
            botao_favoritar_player.icon_color = cor("destaque") if eh_favorita else cor("texto_secundario")
        else:
            botao_favoritar_player.icon_color = cor("texto_secundario")
        botao_aleatorio.icon_color = cor("destaque") if estado["aleatorio"] else cor("texto_secundario")
        botao_ordem_alfabetica.icon_color = cor("destaque") if estado["ordenar_alfabeticamente"] else cor("texto_secundario")
        slider_volume.active_color = cor("destaque")
        switch_seguir_letra.active_color = cor("destaque")
        campo_busca.fill_color = cor("palavra_clicavel")
        campo_busca_palavras.fill_color = cor("palavra_clicavel")
        menu_contexto_musica.bgcolor = cor("cartao")
        menu_contexto_musica.shadow = ft.BoxShadow(blur_radius=20, spread_radius=-2, offset=ft.Offset(0, 6), color=cor("sombra"))
        texto_titulo_menu.color = cor("texto_secundario")
        icone_favoritar_menu.color = cor("destaque")
        texto_favoritar_menu.color = cor("destaque")
        icone_excluir_menu.color = cor("erro")
        texto_excluir_menu.color = cor("erro")
        campo_url_spotdl.bgcolor = cor("cartao")
        texto_palavra_dialogo.color = cor("destaque")
        botao_fechar_dialogo_palavra.icon_color = cor("texto_secundario")
        painel_defi.aplicar_tema()

        for externo, etiqueta, texto_etiqueta in cartoes_criados:
            externo.bgcolor = cor("cartao")
            externo.shadow = ft.BoxShadow(blur_radius=22, spread_radius=-4, offset=ft.Offset(0, 8), color=cor("sombra"))
            etiqueta.bgcolor = cor("cartao_claro")
            texto_etiqueta.color = cor("destaque")

        redesenhar_seletores()
        redesenhar_lista_de_musicas()
        atualizar_letra_na_tela()

    def alternar_tema(e):
        estado["escuro"] = not estado["escuro"]
        aplicar_tema()
        pagina.update()

    def simbolo_decorativo(texto: str, tamanho: int, angulo: float, **posicao):
        return ft.Container(
            **posicao,
            rotate=ft.Rotate(angulo),
            opacity=0.32,
            content=ft.Text(texto, size=tamanho, color=cor("destaque")),
        )

    def criar_borrao(cor_blob: str, tamanho: int, opacidade: float, **posicao):
        return ft.Container(
            **posicao,
            width=tamanho, height=tamanho,
            border_radius=tamanho,
            blur=70,
            gradient=ft.RadialGradient(
                colors=[ft.Colors.with_opacity(opacidade, cor_blob), ft.Colors.with_opacity(0, cor_blob)],
            ),
        )

    camada_fundo = ft.Stack(
        expand=True,
        controls=[
            criar_borrao("#5b8ff9", 520, 0.30, top=-140, left=-120),
            criar_borrao("#ff8fc4", 620, 0.28, top=120, left=260),
            criar_borrao("#a78bfa", 560, 0.26, bottom=-160, right=-120),
            criar_borrao("#ff8fc4", 420, 0.18, bottom=40, left=560),
            criar_borrao("#5b8ff9", 380, 0.16, top=260, right=80),
        ],
    )

    camada_decorativa = ft.Stack(
        expand=True,
        controls=[
            simbolo_decorativo("⋆.ೃ࿔🌸*:･", 22, -0.05, top=16, left=320),
            simbolo_decorativo("ִֶָ𓂃 ࣪˖", 24, 0.08, top=70, right=50),
            simbolo_decorativo("ִֶָ🐇་༘࿐", 22, 0.05, bottom=130, left=330),
            simbolo_decorativo("⋆˚꩜｡", 26, -0.08, bottom=110, right=70),
            simbolo_decorativo("⋆˚꩜｡", 18, 0.1, top=380, left=8),
        ],
    )

    pagina.add(
        ft.Stack(
            expand=True,
            controls=[
                camada_fundo,
                camada_decorativa,
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Row(expand=True, spacing=0, controls=[barra_lateral, area_principal]),
                        barra_agora_tocando,
                    ],
                ),
                capturador_fechar_menu,
                menu_contexto_musica,
            ],
        )
    )

    redesenhar_seletores()
    atualizar_lista_de_musicas_ui()

    if lista_de_musicas:
        await selecionar_musica(lista_de_musicas[0])
    pagina.update()


if __name__ == "__main__":
    ft.run(main)
