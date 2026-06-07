"""
Visualizacoes do grafo de noticias da UFRN.

    Estaticas (Matplotlib):
        - Histograma de grau
        - Top-N entidades por PageRank (barras horizontais)
        - Distribuicao de tipos de entidade (pizza)
        - Tamanhos dos componentes conectados

    Interativa (PyVis):
        - Grafo HTML interativo, cor por tipo, tamanho por PageRank
"""
from __future__ import annotations

import os
from collections import Counter

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from pyvis.network import Network

CORES_TIPO = {
    "PESSOA":       "#1f77b4",
    "ORGANIZACAO":  "#ff7f0e",
    "CENTRO":       "#2ca02c",
    "DEPARTAMENTO": "#d62728",
    "PROJETO":      "#9467bd",
    "EVENTO":       "#8c564b",
    "LABORATORIO":  "#e377c2",
    "SISTEMA":      "#17becf",
}


def _ensure_dir(caminho: str) -> None:
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)


def hist_grau(G: nx.Graph, caminho: str) -> None:
    """Histograma da distribuicao de grau."""
    _ensure_dir(caminho)
    graus = [d for _, d in G.degree()]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(graus, bins=30, color="steelblue", edgecolor="black")
    ax.set_title("Distribuicao de grau dos nos")
    ax.set_xlabel("Grau"); ax.set_ylabel("Numero de nos")
    plt.tight_layout(); fig.savefig(caminho, dpi=120); plt.close(fig)


def top_pagerank(df: pd.DataFrame, caminho: str, top: int = 15) -> None:
    """Top-N entidades por PageRank."""
    _ensure_dir(caminho)
    sub = df.nlargest(top, "pagerank").iloc[::-1]
    cores = [CORES_TIPO.get(t, "#999999") for t in sub["tipo"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(sub["node"], sub["pagerank"], color=cores)
    ax.set_xlabel("PageRank"); ax.set_title(f"Top {top} entidades por PageRank")
    plt.tight_layout(); fig.savefig(caminho, dpi=120); plt.close(fig)


def distribuicao_tipos(G: nx.Graph, caminho: str) -> None:
    """Grafico de pizza com a distribuicao de tipos de no."""
    _ensure_dir(caminho)
    tipos = Counter(d.get("tipo", "?") for _, d in G.nodes(data=True))
    labels, valores = zip(*tipos.most_common()) if tipos else ([], [])
    cores = [CORES_TIPO.get(t, "#999999") for t in labels]
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(valores, labels=labels, colors=cores, autopct="%1.1f%%", startangle=90)
    ax.set_title("Distribuicao de tipos de entidade")
    plt.tight_layout(); fig.savefig(caminho, dpi=120); plt.close(fig)


def tamanho_componentes(G: nx.Graph, caminho: str) -> None:
    """Barras com tamanho de cada componente conectada (top 20)."""
    _ensure_dir(caminho)
    tamanhos = sorted((len(c) for c in nx.connected_components(G)), reverse=True)[:20]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(range(1, len(tamanhos)+1), tamanhos, color="teal")
    ax.set_yscale("log")
    ax.set_xlabel("Indice da componente"); ax.set_ylabel("Numero de nos (log)")
    ax.set_title("Tamanho das 20 maiores componentes conectadas")
    plt.tight_layout(); fig.savefig(caminho, dpi=120); plt.close(fig)


def grafo_estatico(G: nx.Graph, df: pd.DataFrame, caminho: str, top: int = 60) -> None:
    """
    Visualizacao estatica do grafo (apenas os top-N nos por PageRank).
    Layout spring; cor por tipo; tamanho por PageRank.
    """
    _ensure_dir(caminho)
    top_nodes = list(df.nlargest(top, "pagerank")["node"])
    H = G.subgraph(top_nodes).copy()
    if H.number_of_nodes() == 0:
        return
    pos = nx.spring_layout(H, seed=42, k=0.8)
    tipos = [H.nodes[n].get("tipo", "?") for n in H.nodes()]
    cores = [CORES_TIPO.get(t, "#999999") for t in tipos]
    pr_map = dict(zip(df["node"], df["pagerank"]))
    sizes = [200 + 8000 * pr_map.get(n, 0) for n in H.nodes()]

    fig, ax = plt.subplots(figsize=(12, 9))
    nx.draw_networkx_edges(H, pos, alpha=0.25, width=0.6, ax=ax)
    nx.draw_networkx_nodes(H, pos, node_color=cores, node_size=sizes, alpha=0.85, ax=ax)
    nx.draw_networkx_labels(H, pos, font_size=8, ax=ax)
    ax.set_title(f"Grafo estatico - top {top} entidades por PageRank")
    ax.set_axis_off()
    plt.tight_layout(); fig.savefig(caminho, dpi=140); plt.close(fig)


def grafo_interativo(
    G: nx.Graph,
    df: pd.DataFrame,
    caminho: str,
    top: int = 150,
) -> None:
    """
    Grafo interativo PyVis (HTML autossuficiente).
    Limita aos top-N por PageRank para evitar arquivo gigante.
    """
    _ensure_dir(caminho)
    top_nodes = set(df.nlargest(top, "pagerank")["node"])
    H = G.subgraph(top_nodes).copy()

    net = Network(
        height="700px", width="100%", bgcolor="#ffffff", font_color="#222222",
        directed=False, notebook=False, cdn_resources="in_line",
    )
    net.barnes_hut(gravity=-2500, central_gravity=0.3, spring_length=120)

    pr_map = dict(zip(df["node"], df["pagerank"]))
    for n in H.nodes():
        tipo = H.nodes[n].get("tipo", "?")
        cor = CORES_TIPO.get(tipo, "#999999")
        pr = pr_map.get(n, 0)
        tam = 8 + 60 * pr
        freq = H.nodes[n].get("frequencia", 0)
        titulo = f"{n}\nTipo: {tipo}\nPageRank: {pr:.4f}\nFrequencia: {freq}"
        net.add_node(n, label=n, color=cor, size=tam, title=titulo, group=tipo)

    for u, v, data in H.edges(data=True):
        peso = data.get("weight", 1)
        net.add_edge(u, v, value=peso)

    # PyVis usa open() sem encoding (CP1252 no Windows -> falha em acentos).
    # Geramos o HTML em memoria e gravamos com UTF-8 explicito.
    net.generate_html()
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(net.html)


def comparacao_aleatorios(
    comparacao: dict,
    caminho: str,
) -> None:
    """Grafico de barras comparando clustering e caminho medio Real x ER x WS."""
    _ensure_dir(caminho)
    if "erro" in comparacao:
        return
    modelos = ["Real", "Erdős–Rényi", "Watts–Strogatz"]
    chaves = ["real", "er", "ws"]
    clusterings = [comparacao[k]["clustering"] for k in chaves]
    caminhos = [comparacao[k]["caminho_medio"] or 0 for k in chaves]
    cores = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(modelos, clusterings, color=cores)
    axes[0].set_title("Coeficiente de agrupamento")
    axes[0].set_ylabel("clustering medio")
    for i, v in enumerate(clusterings):
        axes[0].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)

    axes[1].bar(modelos, caminhos, color=cores)
    axes[1].set_title("Comprimento medio dos caminhos")
    axes[1].set_ylabel("caminho medio")
    for i, v in enumerate(caminhos):
        axes[1].text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)

    fig.suptitle("Rede real vs grafos aleatorios (mesmos parametros)")
    plt.tight_layout(); fig.savefig(caminho, dpi=120); plt.close(fig)


def gerar_todas(
    G: nx.Graph,
    df: pd.DataFrame,
    pasta_imagens: str = "imagens",
    pasta_results: str = "results",
    comparacao: dict | None = None,
) -> dict[str, str]:
    """Gera todas as visualizacoes e retorna dict de caminhos."""
    saidas = {
        "hist_grau":         os.path.join(pasta_imagens, "01_hist_grau.png"),
        "top_pagerank":      os.path.join(pasta_imagens, "02_top_pagerank.png"),
        "distribuicao_tipos": os.path.join(pasta_imagens, "03_distribuicao_tipos.png"),
        "componentes":       os.path.join(pasta_imagens, "04_componentes.png"),
        "grafo_estatico":    os.path.join(pasta_imagens, "05_grafo_estatico.png"),
        "grafo_interativo":  os.path.join(pasta_results,  "grafo_interativo.html"),
    }
    hist_grau(G, saidas["hist_grau"])
    top_pagerank(df, saidas["top_pagerank"])
    distribuicao_tipos(G, saidas["distribuicao_tipos"])
    tamanho_componentes(G, saidas["componentes"])
    grafo_estatico(G, df, saidas["grafo_estatico"])
    grafo_interativo(G, df, saidas["grafo_interativo"])
    if comparacao:
        saidas["comparacao_aleatorios"] = os.path.join(pasta_imagens, "06_real_vs_aleatorio.png")
        comparacao_aleatorios(comparacao, saidas["comparacao_aleatorios"])
    return saidas
