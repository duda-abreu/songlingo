const estado = {
  musicas: [],
  musicaSelecionada: null,
  modo: "ouvir",
  idioma: "pt",
  indiceAtual: -1,
  acertos: 0,
  tentativas: 0,
  palavrasAprendidas: new Set(JSON.parse(localStorage.getItem("songlingo-palavras") || "[]")),
  palavraAtualModal: null,
  musicaAleatoria: false,
  indiceDitado: null,
  fimTrechoDitado: null,
  questoesDitado: 0,
  exercicioTraducao: null,
};

const FRASES_EXTRAS = [
  { en: "I am learning French every day", fr: "J'apprends le français tous les jours" },
  { en: "Where are you going tonight?", fr: "Où vas-tu ce soir ?" },
  { en: "I would like a coffee, please", fr: "Je voudrais un café, s'il vous plaît" },
  { en: "We are listening to music", fr: "Nous écoutons de la musique" },
  { en: "She loves dancing with her friends", fr: "Elle adore danser avec ses amis" },
  { en: "It is a beautiful day", fr: "C'est une belle journée" },
  { en: "I don't understand this sentence", fr: "Je ne comprends pas cette phrase" },
  { en: "Can you help me?", fr: "Est-ce que tu peux m'aider ?" },
  { en: "We will see each other tomorrow", fr: "Nous nous verrons demain" },
  { en: "I miss you", fr: "Tu me manques" },
];

const elementos = {
  listaMusicas: document.getElementById("lista-musicas"),
  campoBusca: document.getElementById("campo-busca"),
  telaMusica: document.getElementById("tela-musica"),
  textoArtista: document.getElementById("texto-artista"),
  textoTitulo: document.getElementById("texto-titulo"),
  campoAudio: document.getElementById("campo-audio"),
  rotuloCampoAudio: document.getElementById("rotulo-campo-audio"),
  botaoMusicaAleatoria: document.getElementById("botao-musica-aleatoria"),
  audio: document.getElementById("audio"),
  botoesModo: document.querySelectorAll(".botao-modo"),
  painelOuvir: document.getElementById("painel-ouvir"),
  painelEstudar: document.getElementById("painel-estudar"),
  painelDitado: document.getElementById("painel-ditado"),
  painelTraduzir: document.getElementById("painel-traduzir"),
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
  etapaDitado: document.getElementById("etapa-ditado"),
  progressoDitado: document.getElementById("progresso-ditado"),
  ouvirDitado: document.getElementById("ouvir-ditado"),
  respostaDitado: document.getElementById("resposta-ditado"),
  feedbackDitado: document.getElementById("feedback-ditado"),
  gabaritoDitado: document.getElementById("gabarito-ditado"),
  revelarDitado: document.getElementById("revelar-ditado"),
  pularDitado: document.getElementById("pular-ditado"),
  conferirDitado: document.getElementById("conferir-ditado"),
  proximoDitado: document.getElementById("proximo-ditado"),
  origemTraducao: document.getElementById("origem-traducao"),
  fraseIngles: document.getElementById("frase-ingles"),
  respostaTraducao: document.getElementById("resposta-traducao"),
  feedbackTraducao: document.getElementById("feedback-traducao"),
  gabaritoTraducao: document.getElementById("gabarito-traducao"),
  revelarTraducao: document.getElementById("revelar-traducao"),
  tentarNovamenteTraducao: document.getElementById("tentar-novamente-traducao"),
  pularTraducao: document.getElementById("pular-traducao"),
  conferirTraducao: document.getElementById("conferir-traducao"),
  proximaTraducao: document.getElementById("proxima-traducao"),
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
    .replace(/[^a-z0-9'’]+/g, " ")
    .replace(/’/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizarEquivalenciasFrancesas(texto) {
  let valor = normalizarParaComparar(texto)
    .replace(/^est ce qu(e)?\s+/, "")
    .replace(/\bne\s+/g, "")
    .replace(/\bn'(?=\w)/g, "");
  const expansoes = { "j'": "je ", "m'": "me ", "t'": "te ", "s'": "se ", "qu'": "que " };
  Object.entries(expansoes).forEach(([contracao, expansao]) => {
    valor = valor.replace(new RegExp(`\\b${contracao}(?=\\w)`, "g"), expansao);
  });
  valor = valor.replace(/^(peux|veux|vas|es|as|dois|sais|viens)\s+tu\b/, (_, verbo) => `tu ${verbo}`);
  return valor.replace(/\s+/g, " ").trim();
}

function avaliarResposta(resposta, esperado) {
  const recebida = normalizarEquivalenciasFrancesas(resposta || "");
  const certa = normalizarEquivalenciasFrancesas(esperado || "");
  if (!recebida || !certa) return { status: "vazio", faltaram: [], sobraram: [] };
  if (recebida === certa) return { status: "certo", faltaram: [], sobraram: [] };

  const recebidas = recebida.split(" ");
  const certas = certa.split(" ");
  const restantes = [...recebidas];
  const faltaram = certas.filter((palavra) => {
    const indice = restantes.indexOf(palavra);
    if (indice < 0) return true;
    restantes.splice(indice, 1);
    return false;
  });
  const erros = faltaram.length + restantes.length;
  const proporcao = 1 - erros / Math.max(certas.length, 1);
  return {
    status: proporcao >= 0.8 ? "certo" : proporcao >= 0.5 ? "quase" : "errado",
    faltaram,
    sobraram: restantes,
  };
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
  window.fecharCursoDefi?.();
  estado.indiceAtual = -1;
  estado.acertos = 0;
  estado.tentativas = 0;
  estado.indiceDitado = null;
  estado.fimTrechoDitado = null;
  estado.questoesDitado = 0;
  estado.exercicioTraducao = null;

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

  const avaliacao = avaliarResposta(elementos.campoResposta.value, alvo.entrada[estado.idioma]);
  estado.tentativas++;

  if (avaliacao.status === "certo") {
    estado.acertos++;
    estado.palavrasAprendidas.add(alvo.chave);
    localStorage.setItem("songlingo-palavras", JSON.stringify([...estado.palavrasAprendidas]));
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
  localStorage.setItem("songlingo-palavras", JSON.stringify([...estado.palavrasAprendidas]));
  elementos.resultadoModal.textContent = `é "${alvo.entrada[estado.idioma]}".`;
  elementos.resultadoModal.className = "resultado-modal";
  montarPainelEstudo();
}

function atualizarPlacar() {
  elementos.textoPlacar.textContent = `acertos: ${estado.acertos} / ${estado.tentativas}`;
}

window.songlingoTemMusica = () => Boolean(estado.musicaSelecionada);

function escolherMusicaAleatoria() {
  if (!estado.musicas.length) return null;
  const candidatas = estado.musicas.filter((musica) => musica !== estado.musicaSelecionada);
  const opcoes = candidatas.length ? candidatas : estado.musicas;
  return opcoes[Math.floor(Math.random() * opcoes.length)];
}

function alternarMusicaAleatoria() {
  estado.musicaAleatoria = !estado.musicaAleatoria;
  elementos.botaoMusicaAleatoria.classList.toggle("ativo", estado.musicaAleatoria);
  elementos.botaoMusicaAleatoria.textContent = estado.musicaAleatoria
    ? "⇄ aleatório ligado"
    : "⇄ modo aleatório";
  if (estado.musicaAleatoria) {
    const proxima = escolherMusicaAleatoria();
    if (proxima) selecionarMusica(proxima);
  }
}

function pareceFrances(texto) {
  const palavras = normalizarParaComparar(texto).split(" ").filter(Boolean);
  const francesas = new Set(["au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "est", "et", "il", "je", "la", "le", "les", "mais", "me", "mes", "moi", "mon", "ne", "nous", "on", "ou", "pas", "pour", "que", "qui", "se", "si", "son", "sur", "ta", "te", "tes", "toi", "ton", "tout", "tu", "un", "une", "vous", "y"]);
  const inglesas = new Set(["a", "and", "are", "baby", "but", "can", "come", "do", "don't", "for", "girl", "got", "have", "i", "i'm", "in", "is", "it", "love", "me", "my", "not", "of", "on", "right", "the", "this", "to", "wanna", "want", "we", "what", "you", "your"]);
  let frances = palavras.filter((palavra) => francesas.has(palavra)).length;
  const ingles = palavras.filter((palavra) => inglesas.has(palavra)).length;
  frances += palavras.filter((palavra) => /^(j|l|d|c|n|m|t|s|qu)'/.test(palavra)).length;
  frances += [...(texto || "").toLowerCase()].filter((letra) => "àâçéèêëîïôùûüÿœ".includes(letra)).length;
  return palavras.length > 0 && (ingles ? frances > ingles : true);
}

function indicesValidosDitado() {
  const musica = estado.musicaSelecionada;
  if (!musica) return [];
  return musica.linhas
    .map((linha, indice) => ({ indice, palavras: normalizarParaComparar(linha.fr).split(" ").filter(Boolean) }))
    .filter((item) => item.palavras.length >= 2 && item.palavras.length <= 18 && pareceFrances(musica.linhas[item.indice].fr))
    .map((item) => item.indice);
}

function novaPerguntaDitado() {
  const validos = indicesValidosDitado();
  if (!validos.length) {
    elementos.feedbackDitado.textContent = "essa música não tem trechos adequados para ditado.";
    return;
  }
  const opcoes = validos.filter((indice) => indice !== estado.indiceDitado);
  const candidatas = opcoes.length ? opcoes : validos;
  estado.indiceDitado = candidatas[Math.floor(Math.random() * candidatas.length)];
  estado.questoesDitado++;
  estado.fimTrechoDitado = null;

  elementos.etapaDitado.textContent = `trecho ${estado.questoesDitado}`;
  elementos.progressoDitado.value = (estado.questoesDitado - 1) % 10;
  elementos.respostaDitado.value = "";
  elementos.respostaDitado.disabled = false;
  elementos.feedbackDitado.textContent = "";
  elementos.feedbackDitado.className = "feedback-ditado";
  elementos.gabaritoDitado.textContent = "";
  elementos.revelarDitado.hidden = false;
  elementos.pularDitado.hidden = false;
  elementos.conferirDitado.hidden = false;
  elementos.proximoDitado.hidden = true;
}

function tocarTrechoDitado() {
  const musica = estado.musicaSelecionada;
  const indice = estado.indiceDitado;
  if (!musica || indice === null) return;
  if (!elementos.audio.src) {
    elementos.feedbackDitado.textContent = "escolha o arquivo de áudio da música primeiro.";
    elementos.feedbackDitado.className = "feedback-ditado erro";
    return;
  }
  const linha = musica.linhas[indice];
  const proxima = musica.linhas[indice + 1];
  estado.fimTrechoDitado = proxima
    ? Math.max(linha.tempo + 1.2, proxima.tempo - 0.08)
    : Math.min(elementos.audio.duration || linha.tempo + 8, linha.tempo + 8);
  elementos.audio.currentTime = linha.tempo;
  elementos.audio.play();
}

function terminarPerguntaDitado() {
  elementos.respostaDitado.disabled = true;
  elementos.revelarDitado.hidden = true;
  elementos.pularDitado.hidden = true;
  elementos.conferirDitado.hidden = true;
  elementos.proximoDitado.hidden = false;
}

function conferirDitado() {
  const musica = estado.musicaSelecionada;
  if (!musica || estado.indiceDitado === null) return;
  const linha = musica.linhas[estado.indiceDitado];
  const resultado = avaliarResposta(elementos.respostaDitado.value, linha.fr);
  if (resultado.status === "vazio") {
    elementos.feedbackDitado.textContent = "digite o que você ouviu primeiro.";
    elementos.feedbackDitado.className = "feedback-ditado erro";
    return;
  }

  if (resultado.status === "certo") {
    elementos.feedbackDitado.textContent = "certo! você ouviu muito bem. 🌸";
    elementos.feedbackDitado.className = "feedback-ditado acerto";
  } else if (resultado.status === "quase") {
    const detalhes = [];
    if (resultado.faltaram.length) detalhes.push(`faltou: ${resultado.faltaram.join(", ")}`);
    if (resultado.sobraram.length) detalhes.push(`a mais: ${resultado.sobraram.join(", ")}`);
    elementos.feedbackDitado.textContent = `quase! ${detalhes.join(" • ")}`;
    elementos.feedbackDitado.className = "feedback-ditado erro";
  } else {
    elementos.feedbackDitado.textContent = "ainda não. compare sua resposta com a letra.";
    elementos.feedbackDitado.className = "feedback-ditado erro";
  }

  elementos.gabaritoDitado.textContent = `resposta: ${linha.fr}\ntradução: ${linha[estado.idioma] || ""}`;
  terminarPerguntaDitado();
}

function revelarDitado() {
  const musica = estado.musicaSelecionada;
  if (!musica || estado.indiceDitado === null) return;
  const linha = musica.linhas[estado.indiceDitado];
  elementos.feedbackDitado.textContent = "sem problema — ouça acompanhando a resposta.";
  elementos.feedbackDitado.className = "feedback-ditado";
  elementos.gabaritoDitado.textContent = `resposta: ${linha.fr}\ntradução: ${linha[estado.idioma] || ""}`;
  terminarPerguntaDitado();
  tocarTrechoDitado();
}

function exerciciosTraducao() {
  const linhas = estado.musicaSelecionada?.linhas || [];
  const vistos = new Set();
  const exercicios = [];
  linhas.forEach((linha) => {
    const en = (linha.en || "").trim();
    const fr = (linha.fr || "").trim();
    const chave = `${normalizarParaComparar(en)}|${normalizarParaComparar(fr)}`;
    const tamanho = normalizarParaComparar(fr).split(" ").filter(Boolean).length;
    if (en && fr && en !== fr && pareceFrances(fr) && tamanho >= 2 && tamanho <= 18 && !vistos.has(chave)) {
      vistos.add(chave);
      exercicios.push({ en, fr, origem: "música" });
    }
  });
  FRASES_EXTRAS.forEach((frase) => {
    const chave = `${normalizarParaComparar(frase.en)}|${normalizarParaComparar(frase.fr)}`;
    if (!vistos.has(chave)) {
      vistos.add(chave);
      exercicios.push({ ...frase, origem: "prática" });
    }
  });
  return exercicios;
}

function novaTraducao() {
  const exercicios = exerciciosTraducao();
  const opcoes = exercicios.filter((item) => item.en !== estado.exercicioTraducao?.en);
  const candidatas = opcoes.length ? opcoes : exercicios;
  if (!candidatas.length) return;
  estado.exercicioTraducao = candidatas[Math.floor(Math.random() * candidatas.length)];

  elementos.origemTraducao.textContent = estado.exercicioTraducao.origem;
  elementos.fraseIngles.textContent = estado.exercicioTraducao.en;
  elementos.respostaTraducao.value = "";
  elementos.respostaTraducao.disabled = false;
  elementos.feedbackTraducao.textContent = "";
  elementos.feedbackTraducao.className = "feedback-ditado";
  elementos.gabaritoTraducao.textContent = "";
  elementos.revelarTraducao.hidden = false;
  elementos.tentarNovamenteTraducao.hidden = true;
  elementos.pularTraducao.hidden = false;
  elementos.conferirTraducao.hidden = false;
  elementos.proximaTraducao.hidden = true;
}

function terminarTraducao() {
  elementos.respostaTraducao.disabled = true;
  elementos.revelarTraducao.hidden = true;
  elementos.pularTraducao.hidden = true;
  elementos.conferirTraducao.hidden = true;
  elementos.proximaTraducao.hidden = false;
}

function conferirTraducao() {
  const exercicio = estado.exercicioTraducao;
  if (!exercicio) return;
  const resultado = avaliarResposta(elementos.respostaTraducao.value, exercicio.fr);
  if (resultado.status === "vazio") {
    elementos.feedbackTraducao.textContent = "escreva uma tradução primeiro.";
    elementos.feedbackTraducao.className = "feedback-ditado erro";
    return;
  }
  if (resultado.status === "certo") {
    elementos.feedbackTraducao.textContent = "certo! 🌸";
    elementos.feedbackTraducao.className = "feedback-ditado acerto";
  } else if (resultado.status === "quase") {
    const detalhes = [];
    if (resultado.faltaram.length) detalhes.push(`faltou: ${resultado.faltaram.join(", ")}`);
    if (resultado.sobraram.length) detalhes.push(`a mais: ${resultado.sobraram.join(", ")}`);
    elementos.feedbackTraducao.textContent = `quase, mas ainda está errado. ${detalhes.join(" • ")}`;
    elementos.feedbackTraducao.className = "feedback-ditado erro";
  } else {
    elementos.feedbackTraducao.textContent = "errado. compare com a resposta correta.";
    elementos.feedbackTraducao.className = "feedback-ditado erro";
  }
  elementos.gabaritoTraducao.textContent = `resposta: ${exercicio.fr}`;
  terminarTraducao();
}

function revelarTraducao() {
  if (!estado.exercicioTraducao) return;
  elementos.feedbackTraducao.textContent = "resposta mostrada.";
  elementos.feedbackTraducao.className = "feedback-ditado";
  elementos.gabaritoTraducao.textContent = `resposta: ${estado.exercicioTraducao.fr}`;
  terminarTraducao();
  elementos.tentarNovamenteTraducao.hidden = false;
}

function tentarNovamenteTraducao() {
  elementos.respostaTraducao.value = "";
  elementos.respostaTraducao.disabled = false;
  elementos.feedbackTraducao.textContent = "";
  elementos.feedbackTraducao.className = "feedback-ditado";
  elementos.gabaritoTraducao.textContent = "";
  elementos.revelarTraducao.hidden = false;
  elementos.tentarNovamenteTraducao.hidden = true;
  elementos.pularTraducao.hidden = false;
  elementos.conferirTraducao.hidden = false;
  elementos.proximaTraducao.hidden = true;
  elementos.respostaTraducao.focus();
}

function atualizarTelaConformeModo() {
  elementos.painelOuvir.hidden = estado.modo !== "ouvir";
  elementos.painelEstudar.hidden = estado.modo !== "estudar";
  elementos.painelDitado.hidden = estado.modo !== "ditado";
  elementos.painelTraduzir.hidden = estado.modo !== "traduzir";
  if (estado.modo === "ouvir") montarJanelaLetra();
  else if (estado.modo === "estudar") {
    atualizarPlacar();
    montarPainelEstudo();
  } else if (estado.modo === "ditado" && estado.indiceDitado === null) novaPerguntaDitado();
  if (estado.modo === "traduzir" && estado.exercicioTraducao === null) novaTraducao();
}

elementos.campoBusca.addEventListener("input", renderizarListaMusicas);
elementos.botaoMusicaAleatoria.addEventListener("click", alternarMusicaAleatoria);

elementos.campoAudio.addEventListener("change", (e) => {
  const arquivo = e.target.files[0];
  if (!arquivo) return;
  elementos.audio.src = URL.createObjectURL(arquivo);
  elementos.rotuloCampoAudio.textContent = arquivo.name;
});

elementos.audio.addEventListener("timeupdate", () => {
  const musica = estado.musicaSelecionada;
  if (!musica) return;
  if (
    estado.modo === "ditado" &&
    estado.fimTrechoDitado !== null &&
    elementos.audio.currentTime >= estado.fimTrechoDitado
  ) {
    elementos.audio.pause();
    estado.fimTrechoDitado = null;
    return;
  }
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
elementos.ouvirDitado.addEventListener("click", tocarTrechoDitado);
elementos.conferirDitado.addEventListener("click", conferirDitado);
elementos.revelarDitado.addEventListener("click", revelarDitado);
elementos.pularDitado.addEventListener("click", novaPerguntaDitado);
elementos.proximoDitado.addEventListener("click", novaPerguntaDitado);
elementos.conferirTraducao.addEventListener("click", conferirTraducao);
elementos.revelarTraducao.addEventListener("click", revelarTraducao);
elementos.tentarNovamenteTraducao.addEventListener("click", tentarNovamenteTraducao);
elementos.pularTraducao.addEventListener("click", novaTraducao);
elementos.proximaTraducao.addEventListener("click", novaTraducao);
elementos.respostaTraducao.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    conferirTraducao();
  }
});

elementos.audio.addEventListener("ended", () => {
  if (!estado.musicaAleatoria) return;
  const proxima = escolherMusicaAleatoria();
  if (proxima) selecionarMusica(proxima);
});
elementos.respostaDitado.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    conferirDitado();
  }
});
elementos.campoResposta.addEventListener("keydown", (e) => {
  if (e.key === "Enter") conferirResposta();
});
elementos.modal.addEventListener("click", (e) => {
  if (e.target === elementos.modal) fecharModalPalavra();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !elementos.modal.hidden) fecharModalPalavra();
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
