(function () {
  const curso = window.CURSO_DEFI || [];
  const chaveProgresso = "songlingo-defi-progresso";
  const progresso = new Set(JSON.parse(localStorage.getItem(chaveProgresso) || "[]"));
  let unidadeAtual = Math.min(Number(localStorage.getItem("songlingo-defi-unidade") || 0), curso.length - 1);
  let atividadeAtual = 0;
  let opcaoSelecionada = null;
  let conexoesFeitas = new Set();
  let conexaoEsquerda = null;
  let conexaoDireita = null;

  const el = {
    abrir: document.getElementById("abrir-curso-defi"),
    fechar: document.getElementById("fechar-curso-defi"),
    tela: document.getElementById("tela-defi"),
    telaVazia: document.getElementById("tela-vazia"),
    telaMusica: document.getElementById("tela-musica"),
    lista: document.getElementById("lista-unidades-defi"),
    barra: document.getElementById("barra-progresso-defi"),
    nivel: document.getElementById("nivel-defi"),
    tema: document.getElementById("tema-defi"),
    titulo: document.getElementById("titulo-unidade-defi"),
    estado: document.getElementById("estado-unidade-defi"),
    documentoTitulo: document.getElementById("titulo-documento-defi"),
    documento: document.getElementById("texto-documento-defi"),
    ferramentaTitulo: document.getElementById("titulo-ferramentas-defi"),
    ferramenta: document.getElementById("texto-ferramentas-defi"),
    tipo: document.getElementById("tipo-atividade-defi"),
    passos: document.getElementById("passos-defi"),
    pergunta: document.getElementById("pergunta-defi"),
    instrucao: document.getElementById("instrucao-defi"),
    opcoes: document.getElementById("opcoes-defi"),
    resposta: document.getElementById("resposta-defi"),
    feedback: document.getElementById("feedback-defi"),
    gabarito: document.getElementById("gabarito-defi"),
    mostrar: document.getElementById("mostrar-resposta-defi"),
    tentar: document.getElementById("tentar-defi"),
    conferir: document.getElementById("conferir-defi"),
    proxima: document.getElementById("proxima-atividade-defi"),
  };

  function chaveAtividade(indiceUnidade = unidadeAtual, indiceAtividade = atividadeAtual) {
    return `${curso[indiceUnidade].id}:${indiceAtividade}`;
  }

  function salvarProgresso() {
    localStorage.setItem(chaveProgresso, JSON.stringify([...progresso]));
    localStorage.setItem("songlingo-defi-unidade", unidadeAtual);
  }

  function totalAtividades() {
    return curso.reduce((total, unidade) => total + unidade.atividades.length, 0);
  }

  function unidadeConcluida(indice) {
    return curso[indice].atividades.every((_, atividade) => progresso.has(chaveAtividade(indice, atividade)));
  }

  function atualizarProgresso() {
    el.barra.style.width = `${(progresso.size / totalAtividades()) * 100}%`;
    el.estado.textContent = unidadeConcluida(unidadeAtual) ? "✓ atelier concluído" : "em andamento";
  }

  function renderizarLista() {
    el.lista.innerHTML = "";
    let nivelAnterior = "";
    curso.forEach((unidade, indice) => {
      if (unidade.nivel !== nivelAnterior) {
        const nivel = document.createElement("p");
        nivel.className = "divisor-nivel-defi";
        nivel.textContent = unidade.nivel === "B1" ? "passerelle B1" : unidade.nivel;
        el.lista.appendChild(nivel);
        nivelAnterior = unidade.nivel;
      }
      const botao = document.createElement("button");
      botao.type = "button";
      botao.className = "unidade-defi";
      if (indice === unidadeAtual) botao.classList.add("ativa");
      botao.innerHTML = `<span>${unidadeConcluida(indice) ? "✓" : String(indice + 1).padStart(2, "0")}</span><span><strong>${unidade.titulo}</strong><small>${unidade.tema}</small></span>`;
      botao.addEventListener("click", () => selecionarUnidade(indice));
      el.lista.appendChild(botao);
    });
  }

  function selecionarUnidade(indice) {
    unidadeAtual = indice;
    atividadeAtual = 0;
    salvarProgresso();
    renderizarUnidade();
  }

  function renderizarUnidade() {
    const unidade = curso[unidadeAtual];
    el.nivel.textContent = unidade.nivel;
    el.tema.textContent = unidade.tema;
    el.titulo.textContent = unidade.titulo;
    el.documentoTitulo.textContent = unidade.documentoTitulo;
    el.documento.textContent = unidade.documento;
    el.ferramentaTitulo.textContent = unidade.ferramentaTitulo;
    el.ferramenta.textContent = unidade.ferramenta;
    renderizarLista();
    renderizarAtividade();
    atualizarProgresso();
  }

  function renderizarPassos() {
    const atividades = curso[unidadeAtual].atividades;
    el.passos.innerHTML = "";
    atividades.forEach((_, indice) => {
      const passo = document.createElement("button");
      passo.type = "button";
      passo.title = `abrir atividade: ${atividades[indice].tipo}`;
      passo.className = "passo-defi";
      if (indice === atividadeAtual) passo.classList.add("atual");
      if (progresso.has(chaveAtividade(unidadeAtual, indice))) passo.classList.add("feito");
      passo.addEventListener("click", () => {
        atividadeAtual = indice;
        renderizarAtividade();
      });
      el.passos.appendChild(passo);
    });
  }

  function renderizarAtividade() {
    const atividade = curso[unidadeAtual].atividades[atividadeAtual];
    opcaoSelecionada = null;
    conexoesFeitas = new Set();
    conexaoEsquerda = null;
    conexaoDireita = null;
    el.tipo.textContent = atividade.tipo;
    el.pergunta.textContent = atividade.pergunta;
    el.instrucao.textContent = atividade.instrucao || "Escolha ou escreva a melhor resposta em francês.";
    el.feedback.textContent = "";
    el.feedback.className = "feedback-defi";
    el.gabarito.hidden = true;
    el.gabarito.innerHTML = "";
    el.tentar.hidden = true;
    el.mostrar.hidden = false;
    el.conferir.hidden = false;
    el.proxima.hidden = true;
    el.resposta.value = "";
    el.opcoes.innerHTML = "";

    if (atividade.opcoes) {
      el.resposta.hidden = true;
      atividade.opcoes.forEach((opcao, indice) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "opcao-defi";
        botao.textContent = opcao;
        botao.addEventListener("click", () => {
          opcaoSelecionada = indice;
          el.opcoes.querySelectorAll("button").forEach((item) => item.classList.remove("selecionada"));
          botao.classList.add("selecionada");
        });
        el.opcoes.appendChild(botao);
      });
    } else if (atividade.pares) {
      el.resposta.hidden = true;
      el.conferir.hidden = true;
      renderizarAssociacoes(atividade);
    } else {
      el.resposta.hidden = false;
      el.resposta.placeholder = atividade.modelo ? "rédige ta réponse en français" : "écrivez en français";
      if (atividade.audio) renderizarBotaoEscuta(atividade.audio);
    }
    el.conferir.textContent = atividade.modelo ? "terminei" : "conferir";
    renderizarPassos();
  }

  function embaralhar(itens) {
    return [...itens].sort(() => Math.random() - 0.5);
  }

  function renderizarBotaoEscuta(texto) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "botao-ouvir-defi";
    botao.textContent = "▶ écouter";
    botao.addEventListener("click", () => {
      if (!("speechSynthesis" in window)) {
        el.feedback.textContent = "seu navegador não oferece voz francesa.";
        el.feedback.className = "feedback-defi erro";
        return;
      }
      window.speechSynthesis.cancel();
      const fala = new SpeechSynthesisUtterance(texto);
      fala.lang = "fr-FR";
      fala.rate = 0.82;
      window.speechSynthesis.speak(fala);
    });
    el.opcoes.appendChild(botao);
  }

  function renderizarAssociacoes(atividade) {
    const grade = document.createElement("div");
    grade.className = "grade-associacoes-defi";
    const esquerda = document.createElement("div");
    const direita = document.createElement("div");
    esquerda.className = "coluna-associacoes-defi";
    direita.className = "coluna-associacoes-defi";

    embaralhar(atividade.pares.map((par, indice) => ({ texto: par[0], indice }))).forEach((item) => {
      esquerda.appendChild(criarOpcaoAssociacao(item, "esquerda", atividade));
    });
    embaralhar(atividade.pares.map((par, indice) => ({ texto: par[1], indice }))).forEach((item) => {
      direita.appendChild(criarOpcaoAssociacao(item, "direita", atividade));
    });
    grade.append(esquerda, direita);
    el.opcoes.appendChild(grade);
  }

  function criarOpcaoAssociacao(item, lado, atividade) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "opcao-associacao-defi";
    botao.dataset.par = item.indice;
    botao.dataset.lado = lado;
    botao.textContent = item.texto;
    botao.addEventListener("click", () => selecionarAssociacao(botao, item.indice, lado, atividade));
    return botao;
  }

  function selecionarAssociacao(botao, indice, lado, atividade) {
    if (conexoesFeitas.has(indice)) return;
    el.opcoes.querySelectorAll(`[data-lado="${lado}"]`).forEach((item) => item.classList.remove("selecionada"));
    botao.classList.add("selecionada");
    if (lado === "esquerda") conexaoEsquerda = indice;
    else conexaoDireita = indice;
    if (conexaoEsquerda === null || conexaoDireita === null) return;

    if (conexaoEsquerda === conexaoDireita) {
      const indiceCerto = conexaoEsquerda;
      conexoesFeitas.add(indiceCerto);
      el.opcoes.querySelectorAll(`[data-par="${indiceCerto}"]`).forEach((item) => {
        item.classList.remove("selecionada");
        item.classList.add("conectada");
        item.disabled = true;
      });
      el.feedback.textContent = "bonne association !";
      el.feedback.className = "feedback-defi acerto";
      if (conexoesFeitas.size === atividade.pares.length) {
        el.feedback.textContent = "tout est bien relié !";
        marcarConcluida();
      }
    } else {
      el.feedback.textContent = "essa ligação não combina — tente outra.";
      el.feedback.className = "feedback-defi erro";
      el.opcoes.querySelectorAll(".selecionada").forEach((item) => item.classList.remove("selecionada"));
    }
    conexaoEsquerda = null;
    conexaoDireita = null;
  }

  function normalizar(texto) {
    return (texto || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function distancia(a, b) {
    const linha = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i += 1) {
      let anterior = linha[0];
      linha[0] = i;
      for (let j = 1; j <= b.length; j += 1) {
        const atual = linha[j];
        linha[j] = Math.min(linha[j] + 1, linha[j - 1] + 1, anterior + (a[i - 1] === b[j - 1] ? 0 : 1));
        anterior = atual;
      }
    }
    return linha[b.length];
  }

  function respostaAceita(resposta, respostas) {
    const recebida = normalizar(resposta);
    return respostas.some((esperada) => {
      const certa = normalizar(esperada);
      return recebida === certa || distancia(recebida, certa) <= Math.max(1, Math.floor(certa.length * 0.07));
    });
  }

  function marcarConcluida() {
    progresso.add(chaveAtividade());
    salvarProgresso();
    atualizarProgresso();
    renderizarLista();
    renderizarPassos();
    el.conferir.hidden = true;
    el.proxima.hidden = false;
  }

  function conferir() {
    const atividade = curso[unidadeAtual].atividades[atividadeAtual];
    if (atividade.modelo) {
      if (normalizar(el.resposta.value).split(" ").filter(Boolean).length < 5) {
        el.feedback.textContent = "desenvolva um pouco mais sua missão.";
        el.feedback.className = "feedback-defi erro";
        return;
      }
      el.feedback.textContent = "mission accomplie — confira se você incluiu os elementos pedidos.";
      el.feedback.className = "feedback-defi acerto";
      mostrarChecklist(atividade);
      marcarConcluida();
      return;
    }

    const correta = atividade.opcoes
      ? opcaoSelecionada === atividade.correta
      : respostaAceita(el.resposta.value, atividade.respostas);
    if (atividade.opcoes && opcaoSelecionada === null) {
      el.feedback.textContent = "escolha uma opção.";
      el.feedback.className = "feedback-defi erro";
      return;
    }
    if (!atividade.opcoes && !normalizar(el.resposta.value)) {
      el.feedback.textContent = "escreva uma resposta primeiro.";
      el.feedback.className = "feedback-defi erro";
      return;
    }
    if (!correta) {
      el.feedback.textContent = "pas encore — observe o documento e tente outra vez.";
      el.feedback.className = "feedback-defi erro";
      return;
    }
    el.feedback.textContent = `bien vu ! ${atividade.explicacao}`;
    el.feedback.className = "feedback-defi acerto";
    marcarConcluida();
  }

  function mostrarChecklist(atividade) {
    el.gabarito.innerHTML = `<strong>à vérifier</strong><ul>${atividade.checklist.map((item) => `<li>${item}</li>`).join("")}</ul>`;
    el.gabarito.hidden = false;
  }

  function mostrarResposta() {
    const atividade = curso[unidadeAtual].atividades[atividadeAtual];
    if (atividade.modelo) {
      el.gabarito.innerHTML = `<strong>exemple possible</strong><p>${atividade.modelo}</p><ul>${atividade.checklist.map((item) => `<li>${item}</li>`).join("")}</ul>`;
    } else if (atividade.pares) {
      el.gabarito.innerHTML = `<strong>associations</strong><ul>${atividade.pares.map((par) => `<li>${par[0]} → ${par[1]}</li>`).join("")}</ul>`;
    } else {
      const resposta = atividade.opcoes ? atividade.opcoes[atividade.correta] : atividade.resposta;
      el.gabarito.innerHTML = `<strong>réponse</strong><p>${resposta}</p><small>${atividade.explicacao}</small>`;
    }
    el.gabarito.hidden = false;
    el.mostrar.hidden = true;
    el.tentar.hidden = false;
  }

  function tentarNovamente() {
    el.gabarito.hidden = true;
    el.tentar.hidden = true;
    el.mostrar.hidden = false;
    el.feedback.textContent = "";
    el.resposta.focus();
  }

  function proximaAtividade() {
    const ultimaAtividade = curso[unidadeAtual].atividades.length - 1;
    if (atividadeAtual < ultimaAtividade) atividadeAtual += 1;
    else if (unidadeAtual < curso.length - 1) {
      unidadeAtual += 1;
      atividadeAtual = 0;
      salvarProgresso();
      renderizarUnidade();
      return;
    }
    renderizarAtividade();
  }

  function abrirCurso() {
    document.getElementById("audio")?.pause();
    el.telaVazia.hidden = true;
    el.telaMusica.hidden = true;
    el.tela.hidden = false;
    el.abrir.classList.add("ativo");
    renderizarUnidade();
  }

  function fecharCurso() {
    el.tela.hidden = true;
    el.abrir.classList.remove("ativo");
    const temMusica = Boolean(window.songlingoTemMusica?.());
    el.telaMusica.hidden = !temMusica;
    el.telaVazia.hidden = temMusica;
  }

  window.fecharCursoDefi = fecharCurso;
  el.abrir.addEventListener("click", abrirCurso);
  el.fechar.addEventListener("click", fecharCurso);
  el.conferir.addEventListener("click", conferir);
  el.mostrar.addEventListener("click", mostrarResposta);
  el.tentar.addEventListener("click", tentarNovamente);
  el.proxima.addEventListener("click", proximaAtividade);
  el.resposta.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" && !evento.shiftKey && !curso[unidadeAtual].atividades[atividadeAtual].modelo) {
      evento.preventDefault();
      conferir();
    }
  });
})();
