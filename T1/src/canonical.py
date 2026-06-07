"""
Canonicalizacao de entidades nomeadas (synonym resolution).

O NER do spaCy + EntityRuler extrai variantes textuais de uma mesma entidade
como nos distintos (ex.: "UFRN" e "Universidade Federal do Rio Grande do Norte").
Esse modulo aplica um dicionario manual de aliases para colapsar variantes
no mesmo nome canonico.

Decisao metodologica: usamos mapeamento manual (nao fuzzy matching) por dois
motivos: (1) controle total sobre o que e considerado sinonimo, (2) o dominio
e pequeno e bem conhecido. Para escala maior, considerar dedupe.io ou
record-linkage.
"""
from __future__ import annotations

import unicodedata


def _normalizar(texto: str) -> str:
    """Lower + remove acentos + colapsa espacos. Usada como chave de lookup."""
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )
    return " ".join(sem_acentos.lower().split())


# Mapa de aliases -> nome canonico.
# A chave e a versao normalizada (_normalizar) do alias.
# O valor e o nome canonico exibido no grafo.
_ALIASES_RAW: dict[str, str] = {
    # Universidade
    "universidade federal do rio grande do norte": "UFRN",
    "ufrn": "UFRN",

    # Centros e Institutos
    "instituto metropole digital": "Instituto Metrópole Digital",
    "imd": "Instituto Metrópole Digital",
    "escola de ciencias e tecnologia": "Escola de Ciências e Tecnologia",
    "ect": "Escola de Ciências e Tecnologia",
    "centro de tecnologia": "Centro de Tecnologia",
    "centro de biociencias": "Centro de Biociências",
    "centro de ciencias exatas e da terra": "Centro de Ciências Exatas e da Terra",
    "ccet": "Centro de Ciências Exatas e da Terra",
    "centro de ciencias humanas, letras e artes": "Centro de Ciências Humanas, Letras e Artes",
    "cchla": "Centro de Ciências Humanas, Letras e Artes",
    "centro de ciencias da saude": "Centro de Ciências da Saúde",
    "ccs": "Centro de Ciências da Saúde",
    "centro de ciencias sociais aplicadas": "Centro de Ciências Sociais Aplicadas",
    "ccsa": "Centro de Ciências Sociais Aplicadas",
    "centro de educacao": "Centro de Educação",

    # Departamentos
    "departamento de engenharia de computacao e automacao": "Departamento de Engenharia de Computação e Automação",
    "dca": "Departamento de Engenharia de Computação e Automação",
    "departamento de informatica e matematica aplicada": "Departamento de Informática e Matemática Aplicada",
    "dimap": "Departamento de Informática e Matemática Aplicada",

    # Orgaos
    "assessoria de comunicacao": "Agecom",
    "agecom": "Agecom",
    "pro-reitoria de extensao": "PROEX",
    "proex": "PROEX",
    "pro-reitoria de pesquisa": "PROPESQ",
    "propesq": "PROPESQ",
    "pro-reitoria de graduacao": "PROGRAD",
    "prograd": "PROGRAD",
    "pro-reitoria de gestao de pessoas": "PROGESP",
    "progesp": "PROGESP",

    # Sistemas
    "sigaa": "SIGAA",
    "sipac": "SIPAC",
    "sigrh": "SIGRH",
}


def canonicalizar(nome: str) -> str:
    """
    Retorna o nome canonico para uma entidade, se houver mapeamento.
    Caso contrario, retorna o nome original (apenas com espacos colapsados).
    """
    chave = _normalizar(nome)
    return _ALIASES_RAW.get(chave, " ".join(nome.split()))


def total_aliases() -> int:
    """Util para diagnostico no notebook."""
    return len(_ALIASES_RAW)


if __name__ == "__main__":
    testes = [
        "Universidade Federal do Rio Grande do Norte",
        "UFRN",
        "ufrn",
        "Instituto Metrópole Digital",
        "Instituto Metropole Digital",
        "Coisa que nao esta no mapa",
    ]
    for t in testes:
        print(f"  {t!r} -> {canonicalizar(t)!r}")
    print(f"\nTotal de aliases: {total_aliases()}")
