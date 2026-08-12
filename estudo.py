import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher


FRASES_EXTRAS = [
    {"en": "I am learning French every day", "fr": "J'apprends le français tous les jours"},
    {"en": "Where are you going tonight?", "fr": "Où vas-tu ce soir ?"},
    {"en": "I would like a coffee, please", "fr": "Je voudrais un café, s'il vous plaît"},
    {"en": "We are listening to music", "fr": "Nous écoutons de la musique"},
    {"en": "She loves dancing with her friends", "fr": "Elle adore danser avec ses amis"},
    {"en": "It is a beautiful day", "fr": "C'est une belle journée"},
    {"en": "I don't understand this sentence", "fr": "Je ne comprends pas cette phrase"},
    {"en": "Can you help me?", "fr": "Est-ce que tu peux m'aider ?"},
    {"en": "We will see each other tomorrow", "fr": "Nous nous verrons demain"},
    {"en": "I miss you", "fr": "Tu me manques"},
]


def normalizar_resposta(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = texto.lower().replace("’", "'")
    texto = re.sub(r"[^a-z0-9']+", " ", texto)
    return " ".join(texto.split())


def normalizar_equivalencias_francesas(texto: str) -> str:
    texto = normalizar_resposta(texto)
    texto = re.sub(r"^est ce qu(?:e)?\s+", "", texto)
    texto = re.sub(r"\bne\s+", "", texto)
    texto = re.sub(r"\bn'(?=\w)", "", texto)
    expansoes = {
        "j'": "je ",
        "m'": "me ",
        "t'": "te ",
        "s'": "se ",
        "qu'": "que ",
    }
    for contracao, expansao in expansoes.items():
        texto = re.sub(rf"\b{re.escape(contracao)}(?=\w)", expansao, texto)
    texto = re.sub(
        r"^(peux|veux|vas|es|as|dois|sais|viens)\s+tu\b",
        lambda match: f"tu {match.group(1)}",
        texto,
    )
    return " ".join(texto.split())


def avaliar_resposta(resposta: str, esperado: str) -> dict:
    resposta_normalizada = normalizar_equivalencias_francesas(resposta)
    esperado_normalizado = normalizar_equivalencias_francesas(esperado)
    if not resposta_normalizada or not esperado_normalizado:
        return {"status": "vazio", "similaridade": 0.0, "faltaram": [], "sobraram": []}

    similaridade = SequenceMatcher(None, resposta_normalizada, esperado_normalizado).ratio()
    palavras_resposta = Counter(resposta_normalizada.split())
    palavras_esperadas = Counter(esperado_normalizado.split())
    faltaram = list((palavras_esperadas - palavras_resposta).elements())
    sobraram = list((palavras_resposta - palavras_esperadas).elements())
    total = max(sum(palavras_esperadas.values()), 1)
    precisao_palavras = 1 - (len(faltaram) + len(sobraram)) / total

    if resposta_normalizada == esperado_normalizado or (similaridade >= 0.9 and precisao_palavras >= 0.8):
        status = "certo"
    elif similaridade >= 0.62 or precisao_palavras >= 0.55:
        status = "quase"
    else:
        status = "errado"

    return {
        "status": status,
        "similaridade": round(similaridade, 3),
        "faltaram": faltaram,
        "sobraram": sobraram,
    }


def parece_frances(texto: str) -> bool:
    normalizado = normalizar_resposta(texto)
    palavras = normalizado.split()
    if not palavras:
        return False

    marcadores_franceses = {
        "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle", "en",
        "est", "et", "il", "je", "la", "le", "les", "mais", "me", "mes", "moi", "mon",
        "ne", "nous", "on", "ou", "pas", "pour", "que", "qui", "se", "si", "son", "sur",
        "ta", "te", "tes", "toi", "ton", "tout", "tu", "un", "une", "vous", "y",
    }
    marcadores_ingleses = {
        "a", "and", "are", "baby", "but", "can", "come", "do", "don't", "for", "girl",
        "got", "have", "i", "i'm", "in", "is", "it", "love", "me", "my", "not", "of", "on",
        "right", "the", "this", "to", "wanna", "want", "we", "what", "you", "your",
    }
    frances = sum(palavra in marcadores_franceses for palavra in palavras)
    ingles = sum(palavra in marcadores_ingleses for palavra in palavras)
    frances += sum(bool(re.match(r"^(?:j|l|d|c|n|m|t|s|qu)'", palavra)) for palavra in palavras)
    frances += sum(caractere in "àâçéèêëîïôùûüÿœ" for caractere in (texto or "").lower())
    return frances > ingles if ingles else True


def indices_validos_para_ditado(linhas: list[dict]) -> list[int]:
    validos = []
    for indice, linha in enumerate(linhas):
        palavras = normalizar_resposta(linha.get("fr", "")).split()
        if 2 <= len(palavras) <= 18 and parece_frances(linha.get("fr", "")):
            validos.append(indice)
    return validos


def exercicios_ingles_para_frances(linhas: list[dict] | None = None) -> list[dict]:
    exercicios = []
    vistos = set()
    for linha in linhas or []:
        ingles = (linha.get("en") or "").strip()
        frances = (linha.get("fr") or "").strip()
        chave = (normalizar_resposta(ingles), normalizar_resposta(frances))
        if (
            ingles
            and frances
            and ingles != frances
            and parece_frances(frances)
            and 2 <= len(normalizar_resposta(frances).split()) <= 18
            and chave not in vistos
        ):
            vistos.add(chave)
            exercicios.append({"en": ingles, "fr": frances, "origem": "música"})

    for frase in FRASES_EXTRAS:
        chave = (normalizar_resposta(frase["en"]), normalizar_resposta(frase["fr"]))
        if chave not in vistos:
            vistos.add(chave)
            exercicios.append({**frase, "origem": "prática"})
    return exercicios


def fim_do_trecho(linhas: list[dict], indice: int, duracao_audio: float = 0.0) -> float:
    inicio = float(linhas[indice]["tempo"])
    if indice + 1 < len(linhas):
        proximo = float(linhas[indice + 1]["tempo"])
        return max(inicio + 1.2, proximo - 0.08)
    if duracao_audio:
        return min(duracao_audio, inicio + 8.0)
    return inicio + 6.0
