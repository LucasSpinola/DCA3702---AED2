"""
Calculo das metricas estruturais do grafo.

Metricas obrigatorias:
    - Numero de nos / arestas / densidade
    - Componentes conectados
    - Grau medio
    - Diametro (na maior componente)
    - Comprimento medio dos caminhos (na maior componente)
    - Coeficiente de agrupamento
    - Transitividade

Centralidades:
    - Degree, Betweenness, Closeness, Eigenvector, PageRank
"""
from __future__ import annotations

import json
import os
from typing import Any

import networkx as nx
import pandas as pd


def _para_simples(G: nx.MultiDiGraph) -> nx.Graph:
    """Reduz MultiDiGraph a Graph simples (sem direcao, sem multiarestas).

    O peso de cada aresta no grafo simples e o numero de relacoes (em qualquer
    direcao) no MultiDiGraph original — captura a forca da co-ocorrencia.
    """
    H = nx.Graph()
    for u, v in G.edges():
        if H.has_edge(u, v):
            H[u][v]["weight"] += 1
        else:
            H.add_edge(u, v, weight=1)
    for n, data in G.nodes(data=True):
        if n in H.nodes:
            H.nodes[n].update(data)
    return H


def metricas_estruturais(G: nx.MultiDiGraph) -> dict[str, Any]:
    """Calcula as metricas obrigatorias do trabalho.

    Trabalha em duas versoes do grafo:
      - G (MultiDiGraph) para contagens basicas
      - H = _para_simples(G) para coeficientes, diametro, caminhos
    """
    H = _para_simples(G)
    n = H.number_of_nodes()
    m = H.number_of_edges()
    componentes = list(nx.connected_components(H))
    componentes.sort(key=len, reverse=True)
    maior_componente = componentes[0] if componentes else set()
    H_maior = H.subgraph(maior_componente).copy() if maior_componente else H

    resultado: dict[str, Any] = {
        "num_nos": n,
        "num_arestas_simples": m,
        "num_arestas_multidigraph": G.number_of_edges(),
        "densidade": nx.density(H) if n > 1 else 0.0,
        "componentes_conectados": len(componentes),
        "tamanho_maior_componente": len(maior_componente),
        "grau_medio": (2 * m / n) if n else 0.0,
        "coeficiente_agrupamento_medio": nx.average_clustering(H) if n else 0.0,
        "transitividade": nx.transitivity(H) if n else 0.0,
    }

    if H_maior.number_of_nodes() > 1:
        try:
            resultado["diametro_maior_componente"] = nx.diameter(H_maior)
            resultado["comprimento_medio_caminhos"] = nx.average_shortest_path_length(H_maior)
        except (nx.NetworkXError, nx.NetworkXPointlessConcept):
            resultado["diametro_maior_componente"] = None
            resultado["comprimento_medio_caminhos"] = None
    else:
        resultado["diametro_maior_componente"] = 0
        resultado["comprimento_medio_caminhos"] = 0.0

    return resultado


def centralidades(G: nx.MultiDiGraph) -> pd.DataFrame:
    """Calcula as 5 centralidades em DataFrame, uma linha por no."""
    H = _para_simples(G)
    deg = nx.degree_centrality(H)
    bet = nx.betweenness_centrality(H)
    clo = nx.closeness_centrality(H)
    try:
        eig = nx.eigenvector_centrality_numpy(H, max_iter=500)
    except (nx.PowerIterationFailedConvergence, nx.AmbiguousSolution):
        eig = {n: 0.0 for n in H.nodes()}
    pr = nx.pagerank(H, alpha=0.85)

    df = pd.DataFrame({
        "node": list(H.nodes()),
        "tipo": [H.nodes[n].get("tipo", "?") for n in H.nodes()],
        "frequencia": [H.nodes[n].get("frequencia", 0) for n in H.nodes()],
        "degree": [deg[n] for n in H.nodes()],
        "betweenness": [bet[n] for n in H.nodes()],
        "closeness": [clo[n] for n in H.nodes()],
        "eigenvector": [eig[n] for n in H.nodes()],
        "pagerank": [pr[n] for n in H.nodes()],
    })
    return df.sort_values("pagerank", ascending=False).reset_index(drop=True)


def salvar_metricas(metricas: dict[str, Any], caminho: str) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2, default=str)


def salvar_ranking(df: pd.DataFrame, caminho: str, top: int = 20) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    df.head(top).to_csv(caminho, index=False, encoding="utf-8")


def contagem_por_tipo_aresta(G: nx.MultiDiGraph) -> dict[str, int]:
    """Distribuicao das arestas por `tipo_relacao` (PERTENCE_A, COLABORA_COM, etc.)."""
    from collections import Counter
    tipos = (data.get("tipo_relacao", "?") for _, _, data in G.edges(data=True))
    return dict(Counter(tipos).most_common())


def comparar_modelos_aleatorios(G: nx.MultiDiGraph, seed: int = 42) -> dict[str, Any]:
    """
    Compara a rede real contra Erdos-Renyi e Watts-Strogatz com mesmos parametros.

    Validacao da hipotese 'small-world':
        - ER tem caminho medio curto mas clustering muito baixo (~densidade).
        - WS tem ambos altos (small-world por construcao).
        - Rede real e 'small-world' se clustering >> ER e caminho medio ~ ER.
    """
    H = _para_simples(G)
    n = H.number_of_nodes()
    m = H.number_of_edges()
    if n < 5 or m == 0:
        return {"erro": "grafo pequeno demais para comparar"}

    p = nx.density(H)
    k = max(2, int(round(2 * m / n)))
    if k % 2 == 1:
        k += 1

    # Real
    clu_real = nx.average_clustering(H)
    cam_real = _caminho_medio_seguro(H)

    # Erdos-Renyi (n, p)
    G_er = nx.erdos_renyi_graph(n, p, seed=seed)
    clu_er = nx.average_clustering(G_er)
    cam_er = _caminho_medio_seguro(G_er)

    # Watts-Strogatz (n, k, p_rewire)
    G_ws = nx.watts_strogatz_graph(n, k, p=0.1, seed=seed)
    clu_ws = nx.average_clustering(G_ws)
    cam_ws = _caminho_medio_seguro(G_ws)

    return {
        "real":  {"n": n, "m": m, "clustering": clu_real, "caminho_medio": cam_real},
        "er":    {"n": n, "p": p,  "clustering": clu_er,   "caminho_medio": cam_er},
        "ws":    {"n": n, "k": k, "p_rewire": 0.1, "clustering": clu_ws, "caminho_medio": cam_ws},
    }


def _caminho_medio_seguro(G: nx.Graph) -> float | None:
    """Caminho medio na maior componente conexa, ou None se nao calculavel."""
    if G.number_of_nodes() < 2:
        return None
    componentes = list(nx.connected_components(G))
    if not componentes:
        return None
    maior = max(componentes, key=len)
    sub = G.subgraph(maior).copy()
    if sub.number_of_nodes() < 2:
        return None
    try:
        return nx.average_shortest_path_length(sub)
    except (nx.NetworkXError, nx.NetworkXPointlessConcept):
        return None


if __name__ == "__main__":
    G = nx.read_graphml("results/grafo.graphml")
    m = metricas_estruturais(G)
    print(json.dumps(m, indent=2, ensure_ascii=False, default=str))
    df = centralidades(G)
    print(df.head(10))
    salvar_metricas(m, "results/metricas.json")
    salvar_ranking(df, "results/ranking_top20.csv", top=20)
