const estado = {
  musicas: [],
  musicaSelecionada: null,
  modo: "ouvir",
  idioma: "pt",
  indiceAtual: -1,
  acertos: 0,
  tentativas: 0,
  palavrasAprendidas: new Set(),
  palavraAtualModal: null,
};

const elementos = {
  listaMusicas: document.getElementById("lista-musicas"),
  campoBusca: document.getElementById("campo-busca"),
  telaVazia: document.getElementById("tela-vazia"),
  telaMusica: document.getElementById("tela-musica"),
  textoArtista: document.getElementById("texto-artista"),
  textoTitulo: document.getElementById("texto-titulo"),
  campoAudio: document.getElementById("campo-audio"),
  rotuloCampoAudio: document.getElementById("rotulo-campo-audio"),
  audio: document.getElementById("audio"),
  botoesModo: document.querySelectorAll(".botao-modo"),
  painelOuvir: document.getElementById("painel-ouvir"),
  painelEstudar: document.getElementById("painel-estudar"),
  switchSeguir: document.getElementById("switch-seguir"),
  janelaLetra: document.getElementById("janela-letra"),
  painelTraducao: document.getElementById("painel-traducao"),
  botoesIdioma: document.querySelectorAll(".botao-idioma"),
  textoPlacar: document.getElementById("texto-placar"),
  listaLetraEstudo: document.getElementById("lista-letra-estudo"),
  botaoTema: document.getElementById("botao-tema"),
  modal: document.getElementById("modal-palavra"),
  textoPalavraModal: document.getElementById("texto-palavra-modal"),
  campoResposta: document.getElementById("campo-resposta"),
  resultadoModal: document.getElementById("resultado-modal"),
  fecharModal: document.getElementById("fechar-modal"),
  botaoNaoSei: document.getElementById("botao-nao-sei"),
  botaoConferir: document.getElementById("botao-conferir"),
};

function normalizarChaveDePalavra(palavra) {
  return palavra.toLowerCase().replace(/^[^\w\u00e0-\u00f6\u00f8-\u00ff]+|[^\w\u00e0-\u00f6\u00f8-\u00ff]+$/gi, "");
}

function normalizarParaComparar(texto) {
  return texto
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
}

function dividirLinhaEmPalavras(linha) {
  return linha.split(" ").filter((p) => p.length > 0);
}

async function carregarDados() {
  const resposta = await fetch("dados.json");
  estado.musicas = await resposta.json();
  renderizarListaMusicas();
}

function renderizarListaMusicas() {
  const filtro = normalizarParaComparar(elementos.campoBusca.value || "");
  elementos.listaMusicas.innerHTML = "";

  estado.musicas
    .filter((musica) => {
      if (!filtro) return true;
      const alvo = normalizarParaComparar(`${musica.titulo} ${musica.artista}`);
      return alvo.includes(filtro);
    })
    .forEach((musica) => {
      const item = document.createElement("div");
      item.className = "item-musica";
      if (musica === estado.musicaSelecionada) item.classList.add("selecionada");
      item.innerHTML = `
        <span class="titulo">${musica.titulo}</span>
        <span class="artista">${musica.artista}</span>
      `;
      item.addEventListener("click", () => selecionarMusica(musica));
      elementos.listaMusicas.appendChild(item);
    });
}

function selecionarMusica(musica) {
  estado.musicaSelecionada = musica;
  estado.indiceAtual = -1;
  estado.acertos = 0;
  estado.tentativas = 0;

  elementos.telaVazia.hidden = true;
  elementos.telaMusica.hidden = false;
  elementos.textoTitulo.textContent = musica.titulo;
  elementos.textoArtista.textContent = musica.artista;
  elementos.rotuloCampoAudio.textContent = "escolher áudio";
  elementos.audio.removeAttribute("src");
  elementos.audio.load();

  elementos.painelTraducao.innerHTML = '<p class="texto-vazio">clique em uma linha da letra pra ver a tradução aqui.</p>';
  atualizarPlacar();
  renderizarListaMusicas();
  atualizarTelaConformeModo();
}

function encontrarIndiceDaLinhaAtual(linhas, tempoAtual) {
  let indice = -1;
  for (let i = 0; i < linhas.length; i++) {
    if (linhas[i].tempo <= tempoAtual) indice = i;
    else break;
  }
  return indice;
}

function montarJanelaLetra() {
  const musica = estado.musicaSelecionada;
  elementos.janelaLetra.innerHTML = "";
  if (!musica) return;

  const linhas = musica.linhas;
  const centro = estado.indiceAtual >= 0 ? estado.indiceAtual : 0;
  const janela = 3;
  const inicio = Math.max(0, centro - janela);
  const fim = Math.min(linhas.length, centro + janela + 1);

  for (let i = inicio; i < fim; i++) {
    const div = document.createElement("div");
    div.className = "linha-letra" + (i === estado.indiceAtual ? " atual" : "");
    div.textContent = linhas[i].fr;
    div.addEventListener("click", () => irParaLinha(i));
    elementos.janelaLetra.appendChild(div);
  }
}

function irParaLinha(indice) {
  const linha = estado.musicaSelecionada.linhas[indice];
  if (elementos.audio.src) {
    elementos.audio.currentTime = linha.tempo;
  }
  mostrarTraducaoDaLinha(indice);
}

function mostrarTraducaoDaLinha(indice) {
  const linha = estado.musicaSelecionada.linhas[indice];
  if (!linha) return;
  elementos.painelTraducao.innerHTML = `
    <p class="texto-vazio">${linha.fr}</p>
    <div class="linha-traducao"><span class="rotulo">pt</span><span>${linha.pt || ""}</span></div>
    <div class="linha-traducao"><span class="rotulo">en</span><span>${linha.en || ""}</span></div>
  `;
}

function montarPainelEstudo() {
  const musica = estado.musicaSelecionada;
  elementos.listaLetraEstudo.innerHTML = "";
  if (!musica) return;

  musica.linhas.forEach((linha, indice) => {
    const linhaDiv = document.createElement("div");
    linhaDiv.className = "linha-estudo" + (indice === estado.indiceAtual ? " atual" : "");

    dividirLinhaEmPalavras(linha.fr).forEach((palavra) => {
      const chave = normalizarChaveDePalavra(palavra);
      const chip = document.createElement("span");
      chip.textContent = palavra;

      if (!chave) {
        chip.className = "palavra-chip sem-clique";
        linhaDiv.appendChild(chip);
        return;
      }

      const entrada = musica.vocabulario[chave];
      const traduzida = estado.palavrasAprendidas.has(chave) && entrada && entrada[estado.idioma];
      chip.className = "palavra-chip" + (traduzida ? " traduzida" : "");
      chip.addEventListener("click", () => abrirModalPalavra(palavra, chave, entrada));
      linhaDiv.appendChild(chip);
    });

    elementos.listaLetraEstudo.appendChild(linhaDiv);
  });
}

function abrirModalPalavra(palavra, chave, entrada) {
  estado.palavraAtualModal = { palavra, chave, entrada };
  elementos.textoPalavraModal.textContent = palavra;
  elementos.campoResposta.value = "";
  elementos.resultadoModal.textContent = "";
  elementos.resultadoModal.className = "resultado-modal";
  elementos.modal.hidden = false;
  elementos.campoResposta.focus();
}

function fecharModalPalavra() {
  elementos.modal.hidden = true;
  estado.palavraAtualModal = null;
}

function conferirResposta() {
  const alvo = estado.palavraAtualModal;
  if (!alvo || !alvo.entrada || !alvo.entrada[estado.idioma]) {
    elementos.resultadoModal.textContent = "ainda não tenho a tradução dessa palavra.";
    elementos.resultadoModal.className = "resultado-modal";
    return;
  }

  const resposta = normalizarParaComparar(elementos.campoResposta.value);
  const esperado = normalizarParaComparar(alvo.entrada[estado.idioma]);
  estado.tentativas++;

  if (resposta && resposta === esperado) {
    estado.acertos++;
    estado.palavrasAprendidas.add(alvo.chave);
    elementos.resultadoModal.textContent = "isso aí! 🌸";
    elementos.resultadoModal.className = "resultado-modal acerto";
    montarPainelEstudo();
  } else {
    elementos.resultadoModal.textContent = `era "${alvo.entrada[estado.idioma]}", tenta a próxima.`;
    elementos.resultadoModal.className = "resultado-modal erro";
  }

  atualizarPlacar();
}

function revelarResposta() {
  const alvo = estado.palavraAtualModal;
  if (!alvo || !alvo.entrada || !alvo.entrada[estado.idioma]) return;
  estado.palavrasAprendidas.add(alvo.chave);
  elementos.resultadoModal.textContent = `é "${alvo.entrada[estado.idioma]}".`;
  elementos.resultadoModal.className = "resultado-modal";
  montarPainelEstudo();
}

function atualizarPlacar() {
  elementos.textoPlacar.textContent = `acertos: ${estado.acertos} / ${estado.tentativas}`;
}

function atualizarTelaConformeModo() {
  elementos.painelOuvir.hidden = estado.modo !== "ouvir";
  elementos.painelEstudar.hidden = estado.modo !== "estudar";
  if (estado.modo === "ouvir") montarJanelaLetra();
  else montarPainelEstudo();
}

elementos.campoBusca.addEventListener("input", renderizarListaMusicas);

elementos.campoAudio.addEventListener("change", (e) => {
  const arquivo = e.target.files[0];
  if (!arquivo) return;
  elementos.audio.src = URL.createObjectURL(arquivo);
  elementos.rotuloCampoAudio.textContent = arquivo.name;
});

elementos.audio.addEventListener("timeupdate", () => {
  const musica = estado.musicaSelecionada;
  if (!musica) return;
  const novoIndice = encontrarIndiceDaLinhaAtual(musica.linhas, elementos.audio.currentTime);
  if (novoIndice !== estado.indiceAtual) {
    estado.indiceAtual = novoIndice;
    atualizarTelaConformeModo();
    if (estado.modo === "ouvir" && elementos.switchSeguir.checked && novoIndice >= 0) {
      mostrarTraducaoDaLinha(novoIndice);
    }
  }
});

elementos.botoesModo.forEach((botao) => {
  botao.addEventListener("click", () => {
    elementos.botoesModo.forEach((b) => b.classList.remove("ativo"));
    botao.classList.add("ativo");
    estado.modo = botao.dataset.modo;
    atualizarTelaConformeModo();
  });
});

elementos.botoesIdioma.forEach((botao) => {
  botao.addEventListener("click", () => {
    elementos.botoesIdioma.forEach((b) => b.classList.remove("ativo"));
    botao.classList.add("ativo");
    estado.idioma = botao.dataset.idioma;
    montarPainelEstudo();
  });
});

elementos.fecharModal.addEventListener("click", fecharModalPalavra);
elementos.botaoConferir.addEventListener("click", conferirResposta);
elementos.botaoNaoSei.addEventListener("click", revelarResposta);
elementos.campoResposta.addEventListener("keydown", (e) => {
  if (e.key === "Enter") conferirResposta();
});
elementos.modal.addEventListener("click", (e) => {
  if (e.target === elementos.modal) fecharModalPalavra();
});

elementos.botaoTema.addEventListener("click", () => {
  const escuro = document.body.classList.toggle("escuro");
  document.body.classList.toggle("claro", !escuro);
  elementos.botaoTema.textContent = escuro ? "🌙" : "☀️";
  localStorage.setItem("songlingo-tema", escuro ? "escuro" : "claro");
});

const temaSalvo = localStorage.getItem("songlingo-tema");
if (temaSalvo === "claro") {
  document.body.classList.remove("escuro");
  document.body.classList.add("claro");
  elementos.botaoTema.textContent = "☀️";
}

carregarDados();
