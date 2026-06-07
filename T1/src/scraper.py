"""
Coleta de noticias do portal UFRN via WordPress REST API.

A pagina https://www.ufrn.br/imprensa/noticias e renderizada por JavaScript:
chama internamente um backend WordPress em:
    https://webcache01-producao.info.ufrn.br/admin/portal-ufrn/wp-json/wp/v2/

Endpoints relevantes:
    noticias-publicadas/?_embed&per_page=N&page=K   - listagem paginada
    noticias/{id}?_embed                            - noticia individual

A resposta JSON traz titulo, conteudo HTML, data, tags, midia destacada etc.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

# Padroes de assinatura jornalistica usados pelas materias da Agecom. Removidos
# antes do NER para nao inflar centralidades de pessoas que sao apenas autoras.
_BYLINE_PATTERNS = [
    re.compile(r"\b(?:Reportagem|Texto|Edi[çc][ãa]o|Por|Fotos?|Arte)\s*:\s*[^.]{1,80}\.?", re.IGNORECASE),
    re.compile(r"\bAg[êe]ncia de Comunica[çc][ãa]o\b[^.]*\.?", re.IGNORECASE),
    re.compile(r"\bAgecom\s*-\s*UFRN\b", re.IGNORECASE),
]


def _remover_bylines(texto: str) -> str:
    """Remove assinaturas tipicas (Reportagem: X, Texto: Y, Agecom-UFRN) do corpo."""
    for pat in _BYLINE_PATTERNS:
        texto = pat.sub(" ", texto)
    return " ".join(texto.split())

API_BASE = "https://webcache01-producao.info.ufrn.br/admin/portal-ufrn/wp-json/wp/v2/"
USER_AGENT = (
    "Mozilla/5.0 (T1-UFRN-Research; educational; "
    "DCA3702@UFRN; contato: lucas.spinola.712@ufrn.edu.br)"
)
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _limpar_html(html: str) -> str:
    """Remove tags HTML, decodifica entidades e normaliza espacos."""
    if not html:
        return ""
    texto = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    return " ".join(texto.split())


def _processar_noticia(raw: dict[str, Any]) -> dict[str, Any]:
    """Converte uma noticia bruta da API em um dict simplificado.

    O portal UFRN usa Advanced Custom Fields (ACF) e armazena o corpo principal
    em `acf.corpo`, deixando `content.rendered` vazio. Tentamos os dois.
    """
    titulo = _limpar_html(raw.get("title", {}).get("rendered", ""))
    acf = raw.get("acf", {}) or {}
    corpo_html = acf.get("corpo") or raw.get("content", {}).get("rendered", "")
    conteudo = _remover_bylines(_limpar_html(corpo_html))
    resumo = _limpar_html(raw.get("excerpt", {}).get("rendered", ""))

    tags = []
    embedded = raw.get("_embedded", {}) or {}
    for grupo in embedded.get("wp:term", []) or []:
        for termo in grupo or []:
            nome = termo.get("name")
            if nome:
                tags.append(nome)

    return {
        "id": raw.get("id"),
        "data": raw.get("date"),
        "slug": raw.get("slug"),
        "url": raw.get("link"),
        "titulo": titulo,
        "resumo": resumo,
        "conteudo": conteudo,
        "tags": tags,
    }


def coletar_noticias(
    limite: int = 150,
    per_page: int = 30,
    pausa_segundos: float = 1.0,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    """
    Coleta `limite` noticias do portal UFRN.

    A API expoe ate ~100 itens por pagina (per_page=100 e o teto do WP).
    Usamos per_page=30 (default da API) para nao sobrecarregar a resposta.

    Pausa de `pausa_segundos` entre paginas para evitar abuso do servico.
    """
    noticias: list[dict[str, Any]] = []
    page = 1
    while len(noticias) < limite:
        url = f"{API_BASE}noticias-publicadas/"
        params = {"_embed": "1", "per_page": per_page, "page": page}
        try:
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
        except requests.HTTPError as e:
            if resp.status_code == 400 and page > 1:
                break
            raise RuntimeError(f"Falha ao buscar pagina {page}: {e}") from e

        # Forca UTF-8 (alguns proxies do UFRN nao declaram charset)
        resp.encoding = "utf-8"
        dados = resp.json()
        if not dados:
            break

        for raw in dados:
            noticias.append(_processar_noticia(raw))
            if len(noticias) >= limite:
                break

        page += 1
        time.sleep(pausa_segundos)

    return noticias[:limite]


def salvar_noticias(noticias: list[dict[str, Any]], caminho: str) -> None:
    """Salva a lista de noticias em JSON com encoding UTF-8."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)


def carregar_noticias(caminho: str) -> list[dict[str, Any]]:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    print("Coletando noticias da UFRN via WP REST API...")
    noticias = coletar_noticias(limite=150)
    print(f"Total coletado: {len(noticias)}")
    if noticias:
        print(f"Primeira: {noticias[0]['titulo'][:80]}...")
    salvar_noticias(noticias, "data/raw/noticias.json")
    print("Salvo em data/raw/noticias.json")
