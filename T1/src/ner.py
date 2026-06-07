"""
Reconhecimento de entidades nomeadas (NER) com spaCy + EntityRuler.

Usa o modelo pt_core_news_lg do spaCy e estende o reconhecimento com
um EntityRuler carregando padroes especificos da UFRN (patterns.json).

Mapeamento de tipos:
    Entidades nativas do modelo:
        PER -> PESSOA
        ORG -> ORGANIZACAO
        LOC -> descartado (nao e tema do trabalho)
        MISC -> descartado
    Entidades do EntityRuler:
        CENTRO, DEPARTAMENTO, PROJETO, EVENTO, LABORATORIO, SISTEMA, ORGANIZACAO
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import spacy
from spacy.language import Language

from .canonical import canonicalizar

PATTERNS_PATH = os.path.join(os.path.dirname(__file__), "patterns.json")
BYLINES_PATH = os.path.join(os.path.dirname(__file__), "bylines.json")


def _carregar_bylines() -> set[str]:
    """Carrega a lista de bylines (nomes de jornalistas a filtrar)."""
    try:
        with open(BYLINES_PATH, "r", encoding="utf-8") as f:
            return {nome.lower() for nome in json.load(f).get("bylines", [])}
    except FileNotFoundError:
        return set()


_BYLINES = _carregar_bylines()

# Mapeamento de tipos nativos do spaCy para nossa taxonomia
TIPO_NATIVO = {
    "PER": "PESSOA",
    "PERSON": "PESSOA",
    "ORG": "ORGANIZACAO",
}

# Tipos do EntityRuler ja vem no nosso vocabulario
TIPOS_VALIDOS = {
    "PESSOA",
    "ORGANIZACAO",
    "CENTRO",
    "DEPARTAMENTO",
    "PROJETO",
    "EVENTO",
    "LABORATORIO",
    "SISTEMA",
}


def carregar_modelo(patterns_path: str = PATTERNS_PATH) -> Language:
    """
    Carrega pt_core_news_lg e adiciona EntityRuler antes do NER nativo.

    O EntityRuler deve vir ANTES do componente 'ner' para que os
    padroes manuais tenham prioridade sobre as predicoes do modelo.
    """
    nlp = spacy.load("pt_core_news_lg")
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
    else:
        ruler = nlp.get_pipe("entity_ruler")

    with open(patterns_path, "r", encoding="utf-8") as f:
        patterns = json.load(f)
    ruler.add_patterns(patterns)
    return nlp


def _normalizar_entidade(texto: str) -> str:
    """Remove pontuacao em volta, normaliza espacos."""
    return re.sub(r"\s+", " ", texto.strip(" ,.;:?!\"'()[]"))


def extrair_entidades(nlp: Language, texto: str) -> list[tuple[str, str]]:
    """
    Aplica o pipeline em `texto` e retorna lista de (entidade, tipo).
    Deduplicada na ordem de aparicao.
    """
    if not texto:
        return []
    doc = nlp(texto)
    vistas: set[tuple[str, str]] = set()
    saida: list[tuple[str, str]] = []
    for ent in doc.ents:
        label = TIPO_NATIVO.get(ent.label_, ent.label_)
        if label not in TIPOS_VALIDOS:
            continue
        nome = canonicalizar(_normalizar_entidade(ent.text))
        if len(nome) < 2:
            continue
        # Filtra bylines (assinaturas de jornalistas da Agecom)
        if label == "PESSOA" and nome.lower() in _BYLINES:
            continue
        chave = (nome.lower(), label)
        if chave in vistas:
            continue
        vistas.add(chave)
        saida.append((nome, label))
    return saida


def processar_noticias(
    noticias: list[dict[str, Any]],
    nlp: Language | None = None,
) -> list[dict[str, Any]]:
    """
    Para cada noticia em `noticias`, extrai entidades do titulo + conteudo.
    Retorna a mesma lista, com a chave 'entidades' adicionada a cada item.
    """
    if nlp is None:
        nlp = carregar_modelo()
    saida = []
    for n in noticias:
        texto = f"{n.get('titulo','')}\n{n.get('conteudo','')}"
        n2 = dict(n)
        n2["entidades"] = extrair_entidades(nlp, texto)
        saida.append(n2)
    return saida


def salvar_entidades(noticias_com_entidades: list[dict[str, Any]], caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(noticias_com_entidades, f, ensure_ascii=False, indent=2)


def carregar_entidades(caminho: str) -> list[dict[str, Any]]:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    from . import scraper as _s

    print("Carregando modelo spaCy...")
    nlp = carregar_modelo()
    noticias = _s.carregar_noticias("data/raw/noticias.json")
    print(f"Processando {len(noticias)} noticias...")
    noticias_proc = processar_noticias(noticias, nlp=nlp)
    total = sum(len(n["entidades"]) for n in noticias_proc)
    print(f"Total de entidades (com duplicatas entre noticias): {total}")
    salvar_entidades(noticias_proc, "data/processed/entidades.json")
    print("Salvo em data/processed/entidades.json")
