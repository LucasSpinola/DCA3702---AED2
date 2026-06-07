"""
Trabalho 1 - DCA3702 (UFRN)
Analise da rede de relacionamentos nas noticias da UFRN.

Modulos:
    scraper       - coleta de noticias via WP REST API
    ner           - extracao de entidades nomeadas (spaCy + EntityRuler)
    graph         - construcao do MultiDiGraph
    analysis      - metricas e centralidades
    visualization - visualizacoes estaticas e interativa
    dashboard     - relatorio HTML autossuficiente
"""

__version__ = "1.0.0"
