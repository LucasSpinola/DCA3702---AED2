"""
Construcao do grafo de relacionamentos entre entidades.

Cada noticia define um conjunto de entidades (PESSOA, ORGANIZACAO, ...).
Duas entidades que co-ocorrem em uma noticia geram uma aresta dirigida
entre elas, cujo tipo depende dos tipos dos nos envolvidos.

Estrutura: MultiDiGraph (NetworkX)
    No  : entidade unica, atributos = {tipo, frequencia}
    Aresta: dirigida, atributos = {tipo_relacao, noticia_id}
"""
from __future__ import annotations

import itertools
import os
from typing import Any

import networkx as nx


# Relacoes assimetricas: a direcao A -> B carrega significado.
# Sao adicionadas como uma unica aresta direcionada de A -> B.
_RELACOES_ASSIMETRICAS = {
    ("PESSOA", "DEPARTAMENTO"):   "PERTENCE_A",
    ("PESSOA", "CENTRO"):         "PERTENCE_A",
    ("PESSOA", "LABORATORIO"):    "PERTENCE_A",
    ("PESSOA", "PROJETO"):        "DESENVOLVE",
    ("PESSOA", "EVENTO"):         "PARTICIPA_DE",
    ("DEPARTAMENTO", "CENTRO"):   "PERTENCE_A",
    ("ORGANIZACAO", "EVENTO"):    "ORGANIZA",
    ("CENTRO", "PROJETO"):        "DESENVOLVE",
    ("DEPARTAMENTO", "PROJETO"):  "DESENVOLVE",
}


def _relacao(tipo_a: str, tipo_b: str) -> tuple[str, bool]:
    """
    Retorna (tipo_relacao, e_simetrica) para um par ordenado de tipos.

    - Se (tipo_a, tipo_b) tem relacao assimetrica conhecida -> direcao A -> B.
    - Se (tipo_b, tipo_a) tem -> direcao B -> A (caller inverte).
    - Caso contrario -> COLABORA_COM (entre orgs) ou RELACIONADO_A (simetricas).
    """
    if (tipo_a, tipo_b) in _RELACOES_ASSIMETRICAS:
        return _RELACOES_ASSIMETRICAS[(tipo_a, tipo_b)], False
    if (tipo_b, tipo_a) in _RELACOES_ASSIMETRICAS:
        return _RELACOES_ASSIMETRICAS[(tipo_b, tipo_a)], False  # caller inverte
    if tipo_a == "ORGANIZACAO" and tipo_b == "ORGANIZACAO":
        return "COLABORA_COM", True
    return "RELACIONADO_A", True


def construir_grafo(noticias_com_entidades: list[dict[str, Any]]) -> nx.MultiDiGraph:
    """
    Constroi o MultiDiGraph a partir das noticias com entidades.

    Cada par ordenado (A, B) de entidades co-ocorrentes na mesma noticia
    gera uma aresta de A -> B. O atributo 'noticia_id' permite rastrear
    qual noticia originou a relacao.
    """
    G = nx.MultiDiGraph()

    # Prioridade de tipos: se uma entidade aparece com tipos diferentes em
    # noticias distintas, mantemos o mais especifico. Quanto menor o numero,
    # mais especifico (sobrescreve quem ja esta).
    PRIORIDADE = {
        "DEPARTAMENTO": 0, "CENTRO": 0, "LABORATORIO": 0,
        "PROJETO": 1, "EVENTO": 1, "SISTEMA": 1,
        "PESSOA": 2, "ORGANIZACAO": 3,
    }

    for noticia in noticias_com_entidades:
        entidades = noticia.get("entidades", []) or []
        noticia_id = noticia.get("id")

        for nome, tipo in entidades:
            if not G.has_node(nome):
                G.add_node(nome, tipo=tipo, frequencia=0)
            G.nodes[nome]["frequencia"] += 1
            atual = G.nodes[nome].get("tipo", "ORGANIZACAO")
            if PRIORIDADE.get(tipo, 99) < PRIORIDADE.get(atual, 99):
                G.nodes[nome]["tipo"] = tipo

        # Co-ocorrencia: cada par nao ordenado gera 1 aresta (simetrica) OU
        # 1 aresta dirigida (assimetrica). Antes usavamos permutations e
        # criavamos arestas redundantes.
        for (na, ta), (nb, tb) in itertools.combinations(entidades, 2):
            tipo_rel, simetrica = _relacao(ta, tb)
            if simetrica:
                G.add_edge(na, nb, tipo_relacao=tipo_rel, noticia_id=noticia_id)
            elif (ta, tb) in _RELACOES_ASSIMETRICAS:
                G.add_edge(na, nb, tipo_relacao=tipo_rel, noticia_id=noticia_id)
            else:
                # (tb, ta) esta nas assimetricas: aresta vai de b para a
                G.add_edge(nb, na, tipo_relacao=tipo_rel, noticia_id=noticia_id)

    return G


def filtrar_grafo(
    G: nx.MultiDiGraph,
    grau_minimo: int = 2,
) -> nx.MultiDiGraph:
    """
    Remove nos com grau menor que `grau_minimo` (em qualquer direcao).
    Util para reduzir ruido antes de visualizar.
    """
    H = G.copy()
    a_remover = [n for n in H.nodes() if (H.in_degree(n) + H.out_degree(n)) < grau_minimo]
    H.remove_nodes_from(a_remover)
    return H


def salvar_graphml(G: nx.MultiDiGraph, caminho: str) -> None:
    """
    Salva o grafo em GraphML. MultiDiGraph com varias arestas paralelas
    pode ter incompatibilidade com alguns leitores; convertemos pesos
    em atributos string para garantir serializacao.
    """
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    for _, _, data in G.edges(data=True):
        for k, v in list(data.items()):
            if v is None:
                del data[k]
            elif not isinstance(v, (str, int, float, bool)):
                data[k] = str(v)
    for _, data in G.nodes(data=True):
        for k, v in list(data.items()):
            if v is None:
                del data[k]
            elif not isinstance(v, (str, int, float, bool)):
                data[k] = str(v)
    nx.write_graphml(G, caminho)


def salvar_gexf(G: nx.MultiDiGraph, caminho: str) -> None:
    """Salva em GEXF (formato nativo do Gephi). Preserva tipos numericos."""
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    nx.write_gexf(G, caminho)


if __name__ == "__main__":
    from . import ner as _n

    noticias = _n.carregar_entidades("data/processed/entidades.json")
    G = construir_grafo(noticias)
    print(f"Grafo: {G.number_of_nodes()} nos, {G.number_of_edges()} arestas")
    salvar_graphml(G, "results/grafo.graphml")
