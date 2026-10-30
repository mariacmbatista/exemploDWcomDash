"""
=============================================================================
PROJETO PEDAGÓGICO: DASHBOARD MULTIDIMENSIONAL DE VENDAS COM PYTHON DASH & MYSQL DW
Disciplina: Inteligência de Negócios / Data Warehouse & Dashboards
Autora: Professora Maria Batista (UFRPE)
=============================================================================
Este programa exemplifica a integração de ponta a ponta entre:
 1. Um Banco de Dados Data Warehouse (MySQL) modelado no padrão Star Schema (Modelo Estrela).
 2. A biblioteca SQLAlchemy para conexão e execução de consultas.
 3. A biblioteca Pandas para manipulação, agregações multidimensionais e fatiamento (Slice & Dice).
 4. O framework Plotly Dash para criação de uma aplicação web analítica interativa e reativa.

[NOVAS FUNCIONALIDADES IMPLEMENTADAS]:
 - Funcionalidade 1 (Dimensão Tempo): Seleção de período entre datas com dcc.DatePickerRange
   permitindo fatiar o painel para qualquer intervalo customizado de dias/meses/anos.
 - Funcionalidade 2 (Dimensão Geográfica): Seleção dinâmica de Estados da Federação (UF) via
   Checkboxes dependentes da(s) região(ões) escolhida(s). Inicialmente todos os checkboxes vêm
   marcados, permitindo ao usuário desmarcar UFs específicas e atualizar o painel em tempo real.
=============================================================================
"""

# =============================================================================
# SEÇÃO 1: IMPORTAÇÃO DE BIBLIOTECAS E DEPENDÊNCIAS
# =============================================================================

# Módulos nativos do Python para interação com o sistema operacional, buffers e datas
import os        # Leitura de variáveis de ambiente do sistema operacional (ex: credenciais do banco)
import io        # Manipulação de fluxos de entrada/saída em memória (buffer para downloads de arquivos)
import datetime  # Manipulação de datas para carimbos de tempo e nomenclatura de relatórios exportados

# Bibliotecas fundamentais de Ciência de Dados e Processamento Vetorial
import pandas as pd  # Manipulação de DataFrames, filtros tabulares, joins e agregações estatísticas
import numpy as np   # Computação numérica, geração de números aleatórios e arrays multidimensionais

# Framework Plotly Dash para Interfaces Web e Callbacks Reativos
import dash
from dash import (
    dcc,             # Dash Core Components: DatePickerRange, Sliders, Dropdowns, Downloads, Graphs interativos
    html,            # Dash HTML Components: Tags HTML nativas (Div, Header, Button, P, Span, H1-H6)
    dash_table,      # Tabela de dados interativa de alta performance com paginação e formatação
    Input,           # Declara elementos de entrada que DISPARAM automaticamente um callback reativo
    Output,          # Declara elementos visuais de saída que serão ATUALIZADOS pelo callback
    State,           # Captura o valor de um elemento no momento do disparo, SEM disparar o callback
    callback_context # Permite inspecionar qual botão/componente exato causou a invocação do callback
)

# Bibliotecas de Visualização de Dados Científica e Gráfica
import plotly.express as px        # Interface de alto nível para gráficos expressivos e elegantes
import plotly.graph_objects as go  # Interface de baixo nível para construção de gráficos complexos (ex: múltiplos eixos)

# Conexão e Abstração com Banco de Dados Relacional
from sqlalchemy import create_engine, text  # Gerenciador de pool de conexões e execução segura de SQL


# =============================================================================
# SEÇÃO 2: CONFIGURAÇÃO DA CONEXÃO COM O DATA WAREHOUSE (MYSQL)
# =============================================================================
# 

MYSQL_USER = os.getenv("DW_MYSQL_USER", "root")          # Usuário padrão do MySQL
MYSQL_PASS = os.getenv("DW_MYSQL_PASS", "")              # Senha configurada na instalação do MySQL
MYSQL_HOST = os.getenv("DW_MYSQL_HOST", "localhost")     # Servidor local (localhost ou IP da nuvem)
MYSQL_PORT = os.getenv("DW_MYSQL_PORT", "3306")          # Porta padrão do serviço MySQL Server
MYSQL_DB   = os.getenv("DW_MYSQL_DB", "dw_vendas_db")    # Nome do esquema do Data Warehouse

# Construção da Connection String (URL de conexão SQLAlchemy utilizando o driver pymysql)
# O parâmetro charset=utf8mb4 garante suporte nativo a acentuação em português e caracteres especiais
DB_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"


# =============================================================================
# SEÇÃO 3: CARREGAMENTO DE DADOS DO DW E MECANISMO DE FALLBACK
# =============================================================================

def carregar_dados_dw():
    """
    Função responsável pela extração dos dados analíticos (ETL / Query de Apresentação).
    
    [OPERAÇÃO IMPORTANTE - MODELO ESTRELA]:
    Executa um comando SQL SELECT unindo a tabela central FATO_VENDAS às 4 tabelas DIMENSÕES:
      - dim_tempo: provê hierarquia temporal (data, ano, mês, trimestre)
      - dim_produto: provê detalhes de mercadoria (categoria, subcategoria, nome do produto)
      - dim_cliente: provê segmentação mercadológica e localização geográfica (região, estado)
      - dim_canal: provê o canal de distribuição (e-commerce, loja física, televendas, etc.)
      
    Caso o MySQL local dos alunos não esteja rodando, um tratamento de exceção (try/except)
    redireciona para o gerador de dados em memória, garantindo que a aula prática nunca trave.
    """
    query = """
    SELECT 
        f.id_fato,
        t.data,
        t.ano,
        t.mes,
        t.nome_mes,
        t.trimestre,
        p.categoria,
        p.subcategoria,
        p.nome_produto AS produto,
        c.regiao,
        c.estado,
        c.segmento AS cliente_segmento,
        cn.canal_venda,
        f.quantidade,
        f.valor_bruto,
        f.desconto,
        f.valor_liquido,
        f.custo_total,
        f.lucro_liquido,
        -- Cálculo de margem de lucro (%) no próprio banco com proteção contra divisão por zero:
        ROUND((f.lucro_liquido / NULLIF(f.valor_liquido, 0)) * 100, 2) AS margem_lucro
    FROM fato_vendas f
    INNER JOIN dim_tempo t    ON f.id_tempo = t.id_tempo
    INNER JOIN dim_produto p  ON f.id_produto = p.id_produto
    INNER JOIN dim_cliente c  ON f.id_cliente = c.id_cliente
    INNER JOIN dim_canal cn   ON f.id_canal = cn.id_canal
    ORDER BY t.data ASC;
    """
    try:
        # Cria a engine de conexão SQLAlchemy com reciclagem de conexões a cada 1 hora (3600 segundos)
        engine = create_engine(DB_URL, pool_recycle=3600)
        
        # Abre uma sessão de conexão segura através de um Context Manager (with)
        with engine.connect() as conn:
            # pd.read_sql executa o comando no MySQL e converte o resultado diretamente num DataFrame Pandas
            df = pd.read_sql(text(query), conn)
            # Assegura que o campo data seja string formato ISO YYYY-MM-DD
            df['data'] = pd.to_datetime(df['data']).dt.strftime('%Y-%m-%d')
            print(f"[SUCESSO] {len(df)} registros analíticos carregados do MySQL DW ({MYSQL_DB}).")
            return df, "MySQL Conectado"
            
    except Exception as e:
        # Mecanismo de contingência pedagógica para garantir execução imediata mesmo sem banco configurado
        print(f"[AVISO] Não foi possível conectar ao MySQL ({e}).")
        print("[INFO] Carregando dataset multidimensional sintético idêntico em memória para a aula...")
        df_mock = gerar_dataset_multidimensional_demonstracao()
        df_mock['data'] = pd.to_datetime(df_mock['data']).dt.strftime('%Y-%m-%d')
        return df_mock, "Modo Demonstração (SQLite/Memória)"


def gerar_dataset_multidimensional_demonstracao():
    """
    [OPERAÇÃO IMPORTANTE - GERAÇÃO DE DADOS SINTÉTICOS MULTIDIMENSIONAIS]:
    Gera um DataFrame com todas as colunas, tipos de dados e 
    relacionamentos de integridade referencial do Data Warehouse.
    """
    np.random.seed(42)  # Semente fixa para garantir reprodutibilidade exata dos resultados entre os alunos
    n = 1200            # Total de transações da tabela fato a serem simuladas
    
    # Hierarquia da Dimensão Produto (Categoria -> Subcategorias)
    categorias = {
        'Eletrônicos': ['Smartphones', 'Notebooks', 'Tablets', 'Monitores', 'Smart TVs'],
        'Eletrodomésticos': ['Geladeiras', 'Micro-ondas', 'Ar-Condicionado', 'Lava e Seca'],
        'Móveis': ['Cadeiras Ergonômicas', 'Mesas de Escritório', 'Estantes', 'Sofás'],
        'Informática': ['SSDs e Memória', 'Placas de Vídeo', 'Teclados Mecânicos', 'Headsets'],
        'Acessórios': ['Cabos e Hubs', 'Capas e Películas', 'Mochilas', 'Carregadores']
    }
    
    # Hierarquia da Dimensão Cliente Geográfica (Região -> Estados)
    regioes_estados = {
        'Nordeste': ['PE', 'BA', 'CE', 'RN', 'PB'],
        'Sudeste': ['SP', 'RJ', 'MG', 'ES'],
        'Sul': ['PR', 'SC', 'RS'],
        'Centro-Oeste': ['GO', 'MT', 'MS', 'DF'],
        'Norte': ['AM', 'PA', 'RO']
    }
    
    # Canais de Venda e Segmentos de Mercado
    canais = ['E-commerce Web', 'App Mobile', 'Loja Física', 'Marketplace', 'Televendas']
    segmentos = ['Consumidor Final', 'Corporativo (B2B)', 'Pequenas Empresas']
    
    # Dimensão Temporal: Intervalo diário cobrindo múltiplos trimestres e anos
    datas = pd.date_range(start='2024-01-01', end='2026-03-31', freq='D')
    
    registros = []
    for i in range(1, n + 1):
        dt = np.random.choice(datas)
        cat = np.random.choice(list(categorias.keys()))
        subcat = np.random.choice(categorias[cat])
        prod = f"{subcat} Mod. {np.random.randint(100, 999)}"
        regiao = np.random.choice(list(regioes_estados.keys()))
        estado = np.random.choice(regioes_estados[regiao])
        seg = np.random.choice(segmentos, p=[0.55, 0.30, 0.15])
        canal = np.random.choice(canais, p=[0.35, 0.25, 0.20, 0.15, 0.05])
        
        # Métricas quantitativas e financeiras da Fato
        qtd = int(np.random.randint(1, 15))
        preco_unit = float(np.random.uniform(50.0, 3200.0))
        valor_bruto = round(qtd * preco_unit, 2)
        desconto_pct = np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20], p=[0.4, 0.25, 0.2, 0.1, 0.05])
        desconto = round(valor_bruto * desconto_pct, 2)
        valor_liquido = round(valor_bruto - desconto, 2)
        custo_pct = np.uniform = np.random.uniform(0.55, 0.82)
        custo_total = round(valor_liquido * custo_pct, 2)
        lucro_liquido = round(valor_liquido - custo_total, 2)
        margem = round((lucro_liquido / valor_liquido) * 100, 2) if valor_liquido > 0 else 0
        
        # Derivações de atributos de tempo
        mes_dt = pd.to_datetime(dt)
        nome_mes = mes_dt.strftime('%B')
        trimestre = f"T{(mes_dt.month - 1) // 3 + 1}"
        
        registros.append({
            'id_fato': i,
            'data': mes_dt.strftime('%Y-%m-%d'),
            'ano': mes_dt.year,
            'mes': mes_dt.month,
            'nome_mes': nome_mes,
            'trimestre': trimestre,
            'categoria': cat,
            'subcategoria': subcat,
            'produto': prod,
            'regiao': regiao,
            'estado': estado,
            'cliente_segmento': seg,
            'canal_venda': canal,
            'quantidade': qtd,
            'valor_bruto': valor_bruto,
            'desconto': desconto,
            'valor_liquido': valor_liquido,
            'custo_total': custo_total,
            'lucro_liquido': lucro_liquido,
            'margem_lucro': margem
        })
        
    return pd.DataFrame(registros)


# =============================================================================
# SEÇÃO 4: PRÉ-PROCESSAMENTO GLOBAL E CÁLCULO DE LIMITES PARA COMPONENTES
# =============================================================================
# Carregamos o dataset multidimensional principal no escopo da aplicação
df_global, status_fonte = carregar_dados_dw()

# [OPERAÇÃO IMPORTANTE - CÁLCULO DE LIMITES E DATAS]:
# Extraímos os valores mínimos e máximos reais das métricas quantitativas e das datas.
# Esses extremos calibrarão o DatePickerRange e os RangeSliders para que os limites sejam dinâmicos.
MIN_DATA = str(df_global['data'].min())
MAX_DATA = str(df_global['data'].max())

MIN_VALOR = float(df_global['valor_liquido'].min())
MAX_VALOR = float(df_global['valor_liquido'].max())
MIN_MARGEM = float(df_global['margem_lucro'].min())
MAX_MARGEM = float(df_global['margem_lucro'].max())
MIN_QTD = int(df_global['quantidade'].min())
MAX_QTD = int(df_global['quantidade'].max())


# =============================================================================
# SEÇÃO 5: INICIALIZAÇÃO DA APLICAÇÃO DASH E TEMA BOOTSTRAP
# =============================================================================
# Instancia a aplicação Dash configurando título, meta tag de responsividade móvel e
# a folha de estilos CSS do Bootstrap 5 para diagramação de cartões, grids e tipografia.
app = dash.Dash(
    __name__,
    title="DW Analytics - Plotly Dash",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    external_stylesheets=["https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"]
)

# Expõe o servidor Flask subjacente (necessário caso deseje rodar via Gunicorn/WSGI em servidores de produção)
server = app.server


# =============================================================================
# SEÇÃO 6: DEFINIÇÃO DO LAYOUT DA INTERFACE (COMPONENTES VISUAIS E HIERARQUIA)
# =============================================================================
# [CONCEITO DASH LAYOUT]:
# O layout descreve a árvore de componentes visuais do dashboard.
# Ele combina tags HTML puras (html.Div, html.Header) com componentes interativos (dcc.Dropdown, dcc.Graph).
app.layout = html.Div([
    
    # -------------------------------------------------------------------------
    # 6.1 COMPONENTES OCULTOS DE DOWNLOAD
    # -------------------------------------------------------------------------
    # [OPERAÇÃO IMPORTANTE]: Esses componentes não possuem representação visual na tela,
    # mas agem como receptores de fluxo de dados (streams) para exportação em CSV ou Excel.
    dcc.Download(id="download-dataframe-csv"),
    dcc.Download(id="download-dataframe-excel"),

    # -------------------------------------------------------------------------
    # 6.2 CABEÇALHO SUPERIOR (HEADER) COM INFORMAÇÕES E BOTÕES DE AÇÃO
    # -------------------------------------------------------------------------
    html.Header(className="bg-dark text-white p-3 mb-4 shadow-sm", children=[
        html.Div(className="container-fluid d-flex justify-content-between align-items-center flex-wrap gap-2", children=[
            html.Div([
                html.H2("📊 Data Warehouse Multidimensional - Painel Executivo", className="h4 mb-0 fw-bold"),
                html.P(f"Fonte de Dados: {status_fonte} | Modelo Estrela (Star Schema)", className="text-secondary small mb-0")
            ]),
            html.Div(className="d-flex gap-2 align-items-center", children=[
                html.Button("📥 Exportar CSV", id="btn-export-csv", className="btn btn-outline-light btn-sm"),
                html.Button("📗 Exportar Excel (.xlsx)", id="btn-export-excel", className="btn btn-success btn-sm"),
                html.Button("🔄 Recarregar DW", id="btn-refresh-dw", className="btn btn-primary btn-sm")
            ])
        ])
    ]),

    # -------------------------------------------------------------------------
    # 6.3 CORPO PRINCIPAL DO DASHBOARD (SISTEMA DE GRID DE 12 COLUNAS DO BOOTSTRAP)
    # -------------------------------------------------------------------------
    html.Div(className="container-fluid px-4", children=[
        html.Div(className="row g-4", children=[
            
            # =================================================================
            # PAINEL LATERAL ESQUERDO (col-12 col-lg-3): CONTROLES E FILTROS
            # =================================================================
            html.Div(className="col-12 col-lg-3", children=[
                html.Div(className="card shadow-sm border-0 bg-light p-3 sticky-top", style={"top": "15px"}, children=[
                    html.H5("🎯 Filtros Multidimensionais", className="fw-bold mb-3 border-bottom pb-2 text-primary"),

                    # -----------------------------------------------------------------
                    # [NOVA FUNCIONALIDADE 1]: FILTRO DE PERÍODO ENTRE DATAS (DIMENSÃO TEMPO)
                    # -----------------------------------------------------------------
                    # Permite selecionar um intervalo temporal contínuo (data inicial até final).
                    # O componente dcc.DatePickerRange fornece interface com calendário visual.
                    # -----------------------------------------------------------------
                    html.Div(className="mb-3", children=[
                        html.Label("📅 Dimensão Tempo (Período entre Datas):", className="form-label fw-semibold small"),
                        dcc.DatePickerRange(
                            id="filtro-data-range",
                            min_date_allowed=MIN_DATA,
                            max_date_allowed=MAX_DATA,
                            initial_visible_month=MIN_DATA,
                            start_date=MIN_DATA,
                            end_date=MAX_DATA,
                            display_format="DD/MM/YYYY",
                            month_format="MMMM, YYYY",
                            className="w-100",
                            style={"fontSize": "12px"}
                        ),
                        html.Div(className="text-muted mt-1", style={"fontSize": "11px"}, children=[
                            "Filtra os dados da tabela fato entre as duas datas selecionadas."
                        ])
                    ]),

                    # FILTRO TEMPORAL COMPLEMENTAR: Seleção de anos específicos
                    html.Div(className="mb-3", children=[
                        html.Label("📆 Dimensão Tempo (Filtro por Ano):", className="form-label fw-semibold small"),
                        dcc.Dropdown(
                            id="filtro-ano",
                            options=[{"label": str(ano), "value": ano} for ano in sorted(df_global['ano'].unique())],
                            value=sorted(df_global['ano'].unique()),
                            multi=True,
                            placeholder="Selecione os anos..."
                        )
                    ]),

                    # FILTRO 2: Dimensão Produto (Seleção múltipla de categorias)
                    html.Div(className="mb-3", children=[
                        html.Label("📦 Dimensão Produto (Categoria):", className="form-label fw-semibold small"),
                        dcc.Dropdown(
                            id="filtro-categoria",
                            options=[{"label": c, "value": c} for c in sorted(df_global['categoria'].unique())],
                            value=sorted(df_global['categoria'].unique()),
                            multi=True,
                            placeholder="Selecione as categorias..."
                        )
                    ]),

                    # -----------------------------------------------------------------
                    # [NOVA FUNCIONALIDADE 2]: FILTRO HIERÁRQUICO REGIÕES -> ESTADOS (CHECKBOXES)
                    # -----------------------------------------------------------------
                    # 1. O usuário escolhe uma ou mais regiões no Dropdown 'filtro-regiao'.
                    # 2. Um callback reativo lê as regiões escolhidas e popula o Checklist 'filtro-estado'
                    #    apenas com os estados daquelas regiões.
                    # 3. Inicialmente todos os checkboxes dessas regiões começam MARCADOS (dashboard mostra todos).
                    # 4. O usuário pode desmarcar estados específicos para restringir a análise aos selecionados.
                    # -----------------------------------------------------------------
                    html.Div(className="mb-3", children=[
                        html.Label("📍 Dimensão Cliente (Região do País):", className="form-label fw-semibold small"),
                        dcc.Dropdown(
                            id="filtro-regiao",
                            options=[{"label": r, "value": r} for r in sorted(df_global['regiao'].unique())],
                            value=sorted(df_global['regiao'].unique()),
                            multi=True,
                            placeholder="Selecione as regiões..."
                        )
                    ]),

                    # Container dinâmico com os checkboxes de Estados da Federação vinculados às regiões
                    html.Div(id="secao-estados-container", className="mb-3 p-2 bg-white rounded border", children=[
                        html.Div(className="d-flex justify-content-between align-items-center mb-1", children=[
                            html.Label("🗺️ Estados da Federação (UF):", className="form-label fw-semibold small mb-0 text-primary"),
                            html.Span(id="lbl-qtd-estados", className="badge bg-light text-dark border small")
                        ]),
                        html.P(
                            "Inicialmente todos marcados. Desmarque para filtrar estados específicos:",
                            className="text-muted mb-2",
                            style={"fontSize": "11px"}
                        ),
                        dcc.Checklist(
                            id="filtro-estado",
                            options=[{"label": f" {uf}", "value": uf} for uf in sorted(df_global['estado'].unique())],
                            value=sorted(df_global['estado'].unique()),
                            className="small d-flex flex-wrap gap-2",
                            inline=True,
                            inputStyle={"marginRight": "4px", "marginLeft": "4px"}
                        )
                    ]),

                    # FILTRO 4: Dimensão Canal de Venda
                    html.Div(className="mb-3", children=[
                        html.Label("🛒 Dimensão Canal de Venda:", className="form-label fw-semibold small"),
                        dcc.Dropdown(
                            id="filtro-canal",
                            options=[{"label": cn, "value": cn} for cn in sorted(df_global['canal_venda'].unique())],
                            value=sorted(df_global['canal_venda'].unique()),
                            multi=True,
                            placeholder="Selecione os canais..."
                        )
                    ]),

                    # FILTRO 5: Segmento de Clientes (Seleção via Checkboxes)
                    html.Div(className="mb-3", children=[
                        html.Label("👥 Segmento de Cliente:", className="form-label fw-semibold small"),
                        dcc.Checklist(
                            id="filtro-segmento",
                            options=[{"label": f" {s}", "value": s} for s in sorted(df_global['cliente_segmento'].unique())],
                            value=sorted(df_global['cliente_segmento'].unique()),
                            className="small d-flex flex-column gap-1"
                        )
                    ]),

                    html.Hr(),
                    html.H6("🎚️ Faixas de Valores das Métricas", className="fw-bold text-secondary mb-2"),

                    # CONTROLE NUMÉRICO 1: Faixa de Receita Líquida (R$) com RangeSlider
                    html.Div(className="mb-3", children=[
                        html.Div(className="d-flex justify-content-between small text-muted", children=[
                            html.Span("Receita Líquida (R$)"),
                            html.Span(id="lbl-faixa-receita", className="fw-bold text-dark")
                        ]),
                        dcc.RangeSlider(
                            id="slider-receita",
                            min=MIN_VALOR,
                            max=MAX_VALOR,
                            step=100,
                            value=[MIN_VALOR, MAX_VALOR],
                            marks=None,
                            tooltip={"placement": "bottom", "always_visible": False}
                        )
                    ]),

                    # CONTROLE NUMÉRICO 2: Faixa de Margem de Lucro (%) com RangeSlider
                    html.Div(className="mb-3", children=[
                        html.Div(className="d-flex justify-content-between small text-muted", children=[
                            html.Span("Margem de Lucro (%)"),
                            html.Span(id="lbl-faixa-margem", className="fw-bold text-dark")
                        ]),
                        dcc.RangeSlider(
                            id="slider-margem",
                            min=MIN_MARGEM,
                            max=MAX_MARGEM,
                            step=1.0,
                            value=[MIN_MARGEM, MAX_MARGEM],
                            marks=None,
                            tooltip={"placement": "bottom", "always_visible": False}
                        )
                    ]),

                    # CONTROLE NUMÉRICO 3: Faixa de Quantidade de Unidades Vendidas
                    html.Div(className="mb-3", children=[
                        html.Div(className="d-flex justify-content-between small text-muted", children=[
                            html.Span("Quantidade por Venda"),
                            html.Span(id="lbl-faixa-qtd", className="fw-bold text-dark")
                        ]),
                        dcc.RangeSlider(
                            id="slider-qtd",
                            min=MIN_QTD,
                            max=MAX_QTD,
                            step=1,
                            value=[MIN_QTD, MAX_QTD],
                            marks={MIN_QTD: str(MIN_QTD), MAX_QTD: str(MAX_QTD)}
                        )
                    ]),

                    # Botão para Restaurar Estado Original de Todos os Filtros
                    html.Button("↺ Redefinir Todos os Filtros", id="btn-reset-filters", className="btn btn-outline-secondary btn-sm w-100 mt-2")
                ])
            ]),

            # =================================================================
            # ÁREA PRINCIPAL DIREITA (col-12 col-lg-9): CARDS KPI, GRÁFICOS E TABELA
            # =================================================================
            html.Div(className="col-12 col-lg-9", children=[
                
                # 6.4 Linha de Cartões KPI (Preenchida de forma reativa pelo callback)
                html.Div(className="row g-3 mb-4", id="kpi-cards-container"),

                # 6.5 Linha 1 de Gráficos: Temporal (Barra+Linha) e Distribuição por Categorias
                html.Div(className="row g-3 mb-4", children=[
                    html.Div(className="col-12 col-xl-7", children=[
                        html.Div(className="card shadow-sm border-0 p-3", children=[
                            html.H6("📈 Evolução Temporal: Faturamento Líquido e Lucro", className="card-title fw-bold text-primary mb-2"),
                            dcc.Graph(id="grafico-temporal", config={"displayModeBar": True, "responsive": True})
                        ])
                    ]),
                    html.Div(className="col-12 col-xl-5", children=[
                        html.Div(className="card shadow-sm border-0 p-3", children=[
                            html.H6("📊 Faturamento por Categoria de Produto", className="card-title fw-bold text-primary mb-2"),
                            dcc.Graph(id="grafico-categorias", config={"displayModeBar": False, "responsive": True})
                        ])
                    ])
                ]),

                # 6.6 Linha 2 de Gráficos: Comparativo Regional e Dispersão Faturamento vs Margem
                html.Div(className="row g-3 mb-4", children=[
                    html.Div(className="col-12 col-xl-6", children=[
                        html.Div(className="card shadow-sm border-0 p-3", children=[
                            html.H6("🗺️ Desempenho Regional por Estado e Região", className="card-title fw-bold text-primary mb-2"),
                            dcc.Graph(id="grafico-regioes", config={"displayModeBar": False, "responsive": True})
                        ])
                    ]),
                    html.Div(className="col-12 col-xl-6", children=[
                        html.Div(className="card shadow-sm border-0 p-3", children=[
                            html.H6("🎯 Dispersão: Faturamento vs Margem por Canal", className="card-title fw-bold text-primary mb-2"),
                            dcc.Graph(id="grafico-dispersao", config={"displayModeBar": False, "responsive": True})
                        ])
                    ])
                ]),

                # 6.7 Tabela de Dados Analíticos Detalhados (Dash DataTable)
                html.Div(className="card shadow-sm border-0 p-3 mb-4", children=[
                    html.Div(className="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2", children=[
                        html.H6("📋 Visualização Detalhada da Tabela Fato (Dados Filtrados)", className="card-title fw-bold text-secondary mb-0"),
                        html.Span(id="lbl-contador-registros", className="badge bg-primary")
                    ]),
                    dash_table.DataTable(
                        id="tabela-dw",
                        columns=[
                            {"name": "ID", "id": "id_fato"},
                            {"name": "Data", "id": "data"},
                            {"name": "Categoria", "id": "categoria"},
                            {"name": "Produto", "id": "produto"},
                            {"name": "Região", "id": "regiao"},
                            {"name": "Estado", "id": "estado"},
                            {"name": "Canal", "id": "canal_venda"},
                            {"name": "Qtd", "id": "quantidade", "type": "numeric"},
                            {"name": "Receita (R$)", "id": "valor_liquido", "type": "numeric", "format": {"specifier": ",.2f"}},
                            {"name": "Lucro (R$)", "id": "lucro_liquido", "type": "numeric", "format": {"specifier": ",.2f"}},
                            {"name": "Margem (%)", "id": "margem_lucro", "type": "numeric", "format": {"specifier": ".1f"}}
                        ],
                        page_size=10,  # Paginação automática de 10 linhas por página para performance
                        style_table={"overflowX": "auto"},
                        style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold", "color": "#333"},
                        style_cell={"textAlign": "left", "fontSize": "13px", "padding": "8px"}
                    )
                ])
            ])
        ])
    ])
])


# =============================================================================
# SEÇÃO 7: CALLBACKS DE ATUALIZAÇÃO DINÂMICA
# =============================================================================

# -----------------------------------------------------------------------------
# [NOVA FUNCIONALIDADE 2 - CALLBACK CASCATA: REGIÕES -> CHECKBOXES DE ESTADOS]
# -----------------------------------------------------------------------------
# COMENTÁRIO DIDÁTICO:
# Este callback implementa a reatividade em cascata entre a dimensão geográfica macro
# (Região) e a dimensão geográfica micro (Estado/UF).
# Sempre que o usuário seleciona ou altera a(s) região(ões) no dropdown 'filtro-regiao':
#   1. Identificamos todos os estados do Data Warehouse que pertencem a essas regiões.
#   2. Geramos a nova lista de opções (options) para o componente de checklist.
#   3. Conforme requisito pedagógico: INICIALMENTE TODOS os checkboxes das regiões
#      selecionadas começam MARCADOS (value = lista completa dos estados disponíveis).
#   4. O usuário tem total autonomia para desmarcar qualquer estado e afunilar a consulta.
# -----------------------------------------------------------------------------
@app.callback(
    [
        Output("filtro-estado", "options"),
        Output("filtro-estado", "value"),
        Output("lbl-qtd-estados", "children"),
        Output("secao-estados-container", "style")
    ],
    [Input("filtro-regiao", "value")]
)
def atualizar_checkboxes_estados(regioes_selecionadas):
    """
    Atualiza as opções e marcações dos checkboxes de estados da federação
    com base nas regiões escolhidas pelo usuário no Data Warehouse.
    """
    if not regioes_selecionadas:
        # Se nenhuma região estiver selecionada, oculta o container de estados
        return [], [], "0 UFs", {"display": "none"}
    
    # Filtra no DataFrame global os estados pertencentes às regiões ativas
    df_estados = df_global[df_global['regiao'].isin(regioes_selecionadas)]
    estados_disponiveis = sorted(df_estados['estado'].unique())
    
    # Constrói a lista de opções para o dcc.Checklist do Dash
    opcoes = [{"label": f" {uf}", "value": uf} for uf in estados_disponiveis]
    
    # REQUISITO DO PROJETO: Inicialmente todos os checkboxes das regiões selecionadas
    # vêm marcados, de modo que o dashboard exiba todos até que o usuário opte por desmarcar.
    valores_iniciais_marcados = list(estados_disponiveis)
    texto_badge = f"{len(estados_disponiveis)} UFs ativas"
    
    return opcoes, valores_iniciais_marcados, texto_badge, {"display": "block"}


# -----------------------------------------------------------------------------
# CALLBACK PRINCIPAL: REATIVIDADE E ATUALIZAÇÃO GLOBAL DO DASHBOARD
# -----------------------------------------------------------------------------
# [CONCEITO DASH CALLBACK]:
# O decorador @app.callback estabelece o fluxo de dados reativo entre entradas e saídas.
# Sempre que o usuário altera qualquer filtro, período de datas, checkboxes de estados ou
# sliders numéricos (Input), o Dash executa esta função e redistribui os resultados.
# -----------------------------------------------------------------------------
@app.callback(
    [
        # Atualizações visuais dos rótulos de faixas
        Output("lbl-faixa-receita", "children"),
        Output("lbl-faixa-margem", "children"),
        Output("lbl-faixa-qtd", "children"),
        # Atualizações do painel de métricas e gráficos
        Output("kpi-cards-container", "children"),
        Output("grafico-temporal", "figure"),
        Output("grafico-categorias", "figure"),
        Output("grafico-regioes", "figure"),
        Output("grafico-dispersao", "figure"),
        # Atualizações da tabela e contador
        Output("tabela-dw", "data"),
        Output("lbl-contador-registros", "children")
    ],
    [
        # Entradas (Triggers) que acionam a execução do callback:
        # [NOVA FUNCIONALIDADE 1]: Entradas de data inicial e data final do dcc.DatePickerRange
        Input("filtro-data-range", "start_date"),
        Input("filtro-data-range", "end_date"),
        # Demais filtros multidimensionais
        Input("filtro-ano", "value"),
        Input("filtro-categoria", "value"),
        Input("filtro-regiao", "value"),
        # [NOVA FUNCIONALIDADE 2]: Entrada dos checkboxes de estados da federação
        Input("filtro-estado", "value"),
        Input("filtro-canal", "value"),
        Input("filtro-segmento", "value"),
        Input("slider-receita", "value"),
        Input("slider-margem", "value"),
        Input("slider-qtd", "value")
    ]
)
def atualizar_dashboard(data_inicio, data_fim, anos, categorias, regioes, estados, canais, segmentos, faixa_rec, faixa_mrg, faixa_qtd):
    """
    [OPERAÇÃO IMPORTANTE - SLICE & DICE NO PANDAS]:
    Aplica filtros vetoriais sucessivos sobre o DataFrame global carregado em memória.
    Calcula agregações analíticas (GROUP BY) e constrói as 4 figuras Plotly correspondentes.
    """
    # Cria uma cópia rasa para não modificar o DataFrame original global
    df_f = df_global.copy()
    
    # -------------------------------------------------------------------------
    # [NOVA FUNCIONALIDADE 1]:
    # FILTRO TEMPORAL POR PERÍODO ENTRE DATAS (DIMENSÃO TEMPO)
    # A Dimensão Tempo armazena atributos de calendário em nível diário ('data').
    # Aqui fazemos o fatiamento (Slice) do DataFrame pelo intervalo [data_inicio, data_fim].
    # As datas fornecidas pelo dcc.DatePickerRange estão no formato ISO (YYYY-MM-DD).
    # -------------------------------------------------------------------------
    if data_inicio:
        dt_ini_str = str(data_inicio)[:10]
        df_f = df_f[df_f['data'] >= dt_ini_str]
    if data_fim:
        dt_fim_str = str(data_fim)[:10]
        df_f = df_f[df_f['data'] <= dt_fim_str]

    # Filtro complementar por Anos da dimensão tempo
    if anos: 
        df_f = df_f[df_f['ano'].isin(anos)]
        
    # Filtro da dimensão produto por Categorias
    if categorias: 
        df_f = df_f[df_f['categoria'].isin(categorias)]
        
    # Filtro da dimensão geográfica por Regiões
    if regioes: 
        df_f = df_f[df_f['regiao'].isin(regioes)]

    # -------------------------------------------------------------------------
    # [NOVA FUNCIONALIDADE 2]:
    # FILTRO DE ESTADOS DA FEDERAÇÃO POR CHECKBOXES
    # Aplica a restrição de dados aos estados da federação que permanecerem MARCADOS.
    # Caso o usuário desmarque algum estado pertencente às regiões consultadas,
    # a linha correspondente é excluída do DataFrame analítico.
    # -------------------------------------------------------------------------
    if estados is not None and len(estados) > 0:
        df_f = df_f[df_f['estado'].isin(estados)]
    elif regioes and len(regioes) > 0:
        # Se regiões foram selecionadas mas o usuário desmarcou TODOS os checkboxes de estados,
        # o conjunto resultante é vazio (nenhum estado marcado).
        df_f = df_f.iloc[0:0]

    # Filtros de Canais de Venda e Segmento de Clientes
    if canais: 
        df_f = df_f[df_f['canal_venda'].isin(canais)]
    if segmentos: 
        df_f = df_f[df_f['cliente_segmento'].isin(segmentos)]
        
    # -------------------------------------------------------------------------
    # APLICAÇÃO DOS FILTROS POR FAIXAS NUMÉRICAS (MÉTRICAS DA FATO)
    # -------------------------------------------------------------------------
    if faixa_rec: 
        df_f = df_f[(df_f['valor_liquido'] >= faixa_rec[0]) & (df_f['valor_liquido'] <= faixa_rec[1])]
    if faixa_mrg: 
        df_f = df_f[(df_f['margem_lucro'] >= faixa_mrg[0]) & (df_f['margem_lucro'] <= faixa_mrg[1])]
    if faixa_qtd: 
        df_f = df_f[(df_f['quantidade'] >= faixa_qtd[0]) & (df_f['quantidade'] <= faixa_qtd[1])]

    # Formatação amigável das strings de exibição dos limites selecionados
    txt_rec = f"R$ {faixa_rec[0]:,.0f} - R$ {faixa_rec[1]:,.0f}" if faixa_rec else ""
    txt_mrg = f"{faixa_mrg[0]:.1f}% - {faixa_mrg[1]:.1f}%" if faixa_mrg else ""
    txt_qtd = f"{faixa_qtd[0]} a {faixa_qtd[1]} un." if faixa_qtd else ""

    # Tratamento para quando nenhum registro atender aos critérios dos filtros
    if df_f.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Nenhum dado encontrado para os filtros selecionados", template="plotly_white")
        return txt_rec, txt_mrg, txt_qtd, [], empty_fig, empty_fig, empty_fig, empty_fig, [], "0 registros"

    # -------------------------------------------------------------------------
    # CÁLCULO DAS MÉTRICAS AGREGADAS (KPIS EXECUTIVOS)
    # -------------------------------------------------------------------------
    tot_rec = df_f['valor_liquido'].sum()                                  # Faturamento Líquido Total
    tot_luc = df_f['lucro_liquido'].sum()                                  # Lucro Líquido Total
    mrg_med = (tot_luc / tot_rec * 100) if tot_rec > 0 else 0              # Margem Percentual Ponderada
    tkt_med = tot_rec / len(df_f) if len(df_f) > 0 else 0                  # Ticket Médio por Transação
    tot_qtd = df_f['quantidade'].sum()                                     # Volume Total de Peças

    # Construção dinâmica dos Cartões Bootstrap coloridos de KPI
    kpis = [
        html.Div(className="col-12 col-sm-6 col-xl", children=[
            html.Div(className="card shadow-sm border-0 bg-primary text-white p-3", children=[
                html.Span("Receita Líquida Total", className="small opacity-75"),
                html.H4(f"R$ {tot_rec:,.2f}", className="fw-bold mb-0")
            ])
        ]),
        html.Div(className="col-12 col-sm-6 col-xl", children=[
            html.Div(className="card shadow-sm border-0 bg-success text-white p-3", children=[
                html.Span("Lucro Líquido Total", className="small opacity-75"),
                html.H4(f"R$ {tot_luc:,.2f}", className="fw-bold mb-0")
            ])
        ]),
        html.Div(className="col-12 col-sm-6 col-xl", children=[
            html.Div(className="card shadow-sm border-0 bg-info text-white p-3", children=[
                html.Span("Margem de Lucro Média", className="small opacity-75"),
                html.H4(f"{mrg_med:.2f}%", className="fw-bold mb-0")
            ])
        ]),
        html.Div(className="col-12 col-sm-6 col-xl", children=[
            html.Div(className="card shadow-sm border-0 bg-warning text-dark p-3", children=[
                html.Span("Ticket Médio", className="small text-muted"),
                html.H4(f"R$ {tkt_med:,.2f}", className="fw-bold mb-0")
            ])
        ]),
        html.Div(className="col-12 col-sm-6 col-xl", children=[
            html.Div(className="card shadow-sm border-0 bg-secondary text-white p-3", children=[
                html.Span("Volume de Itens Vendidos", className="small opacity-75"),
                html.H4(f"{tot_qtd:,}", className="fw-bold mb-0")
            ])
        ])
    ]

    # -------------------------------------------------------------------------
    # GRÁFICO 1: EVOLUÇÃO TEMPORAL COMPOSTA (BARRA + LINHA)
    # -------------------------------------------------------------------------
    df_tempo = df_f.groupby(['ano', 'mes', 'nome_mes'], as_index=False)[['valor_liquido', 'lucro_liquido']].sum()
    df_tempo['periodo'] = df_tempo['ano'].astype(str) + '-' + df_tempo['mes'].astype(str).str.zfill(2)
    df_tempo = df_tempo.sort_values(by=['ano', 'mes'])

    fig_tempo = go.Figure()
    fig_tempo.add_trace(go.Bar(
        x=df_tempo['periodo'], 
        y=df_tempo['valor_liquido'], 
        name="Receita Líquida (R$)", 
        marker_color="#2563eb"
    ))
    fig_tempo.add_trace(go.Scatter(
        x=df_tempo['periodo'], 
        y=df_tempo['lucro_liquido'], 
        name="Lucro Líquido (R$)", 
        mode="lines+markers", 
        line=dict(color="#10b981", width=3)
    ))
    fig_tempo.update_layout(margin=dict(l=40, r=20, t=20, b=40), template="plotly_white", hovermode="x unified")

    # -------------------------------------------------------------------------
    # GRÁFICO 2: FATURAMENTO POR CATEGORIA DE PRODUTO (BARRA HORIZONTAL)
    # -------------------------------------------------------------------------
    df_cat = df_f.groupby('categoria', as_index=False)['valor_liquido'].sum().sort_values(by='valor_liquido', ascending=True)
    fig_cat = px.bar(
        df_cat, 
        x="valor_liquido", 
        y="categoria", 
        orientation="h", 
        color="valor_liquido", 
        color_continuous_scale="Viridis",
        labels={"valor_liquido": "Faturamento (R$)", "categoria": "Categoria"}
    )
    fig_cat.update_layout(margin=dict(l=40, r=20, t=20, b=40), coloraxis_showscale=False, template="plotly_white")

    # -------------------------------------------------------------------------
    # GRÁFICO 3: DESEMPENHO REGIONAL POR ESTADO (BARRA AGRUPADA)
    # -------------------------------------------------------------------------
    df_reg = df_f.groupby(['regiao', 'estado'], as_index=False)[['valor_liquido', 'lucro_liquido']].sum()
    fig_reg = px.bar(
        df_reg, 
        x="estado", 
        y="valor_liquido", 
        color="regiao", 
        barmode="group",
        labels={"valor_liquido": "Faturamento (R$)", "estado": "UF", "regiao": "Região"}
    )
    fig_reg.update_layout(margin=dict(l=40, r=20, t=20, b=40), template="plotly_white")

    # -------------------------------------------------------------------------
    # GRÁFICO 4: DIAGRAMA DE DISPERSÃO (RECEITA vs MARGEM POR CANAL)
    # -------------------------------------------------------------------------
    fig_disp = px.scatter(
        df_f, 
        x="valor_liquido", 
        y="margem_lucro", 
        color="canal_venda", 
        size="quantidade", 
        hover_data=["produto", "regiao"], 
        opacity=0.7,
        labels={"valor_liquido": "Receita Líquida (R$)", "margem_lucro": "Margem de Lucro (%)", "canal_venda": "Canal"}
    )
    fig_disp.update_layout(margin=dict(l=40, r=20, t=20, b=40), template="plotly_white")

    # -------------------------------------------------------------------------
    # PREPARAÇÃO DA TABELA DE DADOS E CONTADOR DE LINHAS
    # -------------------------------------------------------------------------
    tabela = df_f.head(100).to_dict("records")
    contador = f"{len(df_f)} registros encontrados"

    return txt_rec, txt_mrg, txt_qtd, kpis, fig_tempo, fig_cat, fig_reg, fig_disp, tabela, contador


# =============================================================================
# SEÇÃO 8: CALLBACKS DE EXPORTAÇÃO DE RELATÓRIOS (CSV E EXCEL)
# =============================================================================

@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    [
        State("filtro-data-range", "start_date"),
        State("filtro-data-range", "end_date"),
        State("filtro-ano", "value"), 
        State("filtro-categoria", "value"),
        State("filtro-regiao", "value"), 
        State("filtro-estado", "value"),
        State("filtro-canal", "value"),
        State("filtro-segmento", "value"), 
        State("slider-receita", "value"),
        State("slider-margem", "value"), 
        State("slider-qtd", "value")
    ],
    prevent_initial_call=True
)
def exportar_csv(n_clicks, data_inicio, data_fim, anos, categorias, regioes, estados, canais, segmentos, faixa_rec, faixa_mrg, faixa_qtd):
    """
    Exporta os dados filtrados em formato CSV com codificação UTF-8 com BOM (utf-8-sig).
    """
    df_f = df_global.copy()
    if data_inicio: df_f = df_f[df_f['data'] >= str(data_inicio)[:10]]
    if data_fim: df_f = df_f[df_f['data'] <= str(data_fim)[:10]]
    if anos: df_f = df_f[df_f['ano'].isin(anos)]
    if categorias: df_f = df_f[df_f['categoria'].isin(categorias)]
    if regioes: df_f = df_f[df_f['regiao'].isin(regioes)]
    if estados: df_f = df_f[df_f['estado'].isin(estados)]
    if canais: df_f = df_f[df_f['canal_venda'].isin(canais)]
    if segmentos: df_f = df_f[df_f['cliente_segmento'].isin(segmentos)]
    if faixa_rec: df_f = df_f[(df_f['valor_liquido'] >= faixa_rec[0]) & (df_f['valor_liquido'] <= faixa_rec[1])]
    if faixa_mrg: df_f = df_f[(df_f['margem_lucro'] >= faixa_mrg[0]) & (df_f['margem_lucro'] <= faixa_mrg[1])]
    if faixa_qtd: df_f = df_f[(df_f['quantidade'] >= faixa_qtd[0]) & (df_f['quantidade'] <= faixa_qtd[1])]

    return dcc.send_data_frame(
        df_f.to_csv,
        filename=f"dw_vendas_filtrado_{datetime.date.today().strftime('%Y%m%d')}.csv",
        index=False,
        encoding="utf-8-sig"
    )


@app.callback(
    Output("download-dataframe-excel", "data"),
    Input("btn-export-excel", "n_clicks"),
    [
        State("filtro-data-range", "start_date"),
        State("filtro-data-range", "end_date"),
        State("filtro-ano", "value"), 
        State("filtro-categoria", "value"),
        State("filtro-regiao", "value"), 
        State("filtro-estado", "value"),
        State("filtro-canal", "value"),
        State("filtro-segmento", "value"), 
        State("slider-receita", "value"),
        State("slider-margem", "value"), 
        State("slider-qtd", "value")
    ],
    prevent_initial_call=True
)
def exportar_excel(n_clicks, data_inicio, data_fim, anos, categorias, regioes, estados, canais, segmentos, faixa_rec, faixa_mrg, faixa_qtd):
    """
    Exporta os dados filtrados nativamente para arquivo do Microsoft Excel (.xlsx).
    """
    df_f = df_global.copy()
    if data_inicio: df_f = df_f[df_f['data'] >= str(data_inicio)[:10]]
    if data_fim: df_f = df_f[df_f['data'] <= str(data_fim)[:10]]
    if anos: df_f = df_f[df_f['ano'].isin(anos)]
    if categorias: df_f = df_f[df_f['categoria'].isin(categorias)]
    if regioes: df_f = df_f[df_f['regiao'].isin(regioes)]
    if estados: df_f = df_f[df_f['estado'].isin(estados)]
    if canais: df_f = df_f[df_f['canal_venda'].isin(canais)]
    if segmentos: df_f = df_f[df_f['cliente_segmento'].isin(segmentos)]
    if faixa_rec: df_f = df_f[(df_f['valor_liquido'] >= faixa_rec[0]) & (df_f['valor_liquido'] <= faixa_rec[1])]
    if faixa_mrg: df_f = df_f[(df_f['margem_lucro'] >= faixa_mrg[0]) & (df_f['margem_lucro'] <= faixa_mrg[1])]
    if faixa_qtd: df_f = df_f[(df_f['quantidade'] >= faixa_qtd[0]) & (df_f['quantidade'] <= faixa_qtd[1])]

    return dcc.send_data_frame(
        df_f.to_excel,
        filename=f"dw_vendas_filtrado_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
        index=False,
        sheet_name="DW_Vendas_Filtrado"
    )


# =============================================================================
# SEÇÃO 9: CALLBACK PARA REDEFINIÇÃO DE FILTROS (BOTÃO RESET)
# =============================================================================
@app.callback(
    [
        Output("filtro-data-range", "start_date"),
        Output("filtro-data-range", "end_date"),
        Output("filtro-ano", "value"), 
        Output("filtro-categoria", "value"),
        Output("filtro-regiao", "value"), 
        Output("filtro-estado", "value", allow_duplicate=True),
        Output("filtro-canal", "value"),
        Output("filtro-segmento", "value"), 
        Output("slider-receita", "value"),
        Output("slider-margem", "value"), 
        Output("slider-qtd", "value")
    ],
    Input("btn-reset-filters", "n_clicks"),
    prevent_initial_call=True
)
def resetar_filtros(n_clicks):
    """
    Restaura todos os seletores, datas, estados e RangeSliders para os valores padrão
    originais do conjunto de dados do Data Warehouse.
    """
    return (
        MIN_DATA,
        MAX_DATA,
        sorted(df_global['ano'].unique()),
        sorted(df_global['categoria'].unique()),
        sorted(df_global['regiao'].unique()),
        sorted(df_global['estado'].unique()),
        sorted(df_global['canal_venda'].unique()),
        sorted(df_global['cliente_segmento'].unique()),
        [MIN_VALOR, MAX_VALOR],
        [MIN_MARGEM, MAX_MARGEM],
        [MIN_QTD, MAX_QTD]
    )


# =============================================================================
# SEÇÃO 10: INICIALIZAÇÃO DO SERVIDOR LOCAL DE DESENVOLVIMENTO
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Servidor Plotly Dash Iniciado com Sucesso!")
    print("🌐 Acesse no seu navegador: http://127.0.0.1:8050")
    print("💡 Pressione CTRL+C no terminal para encerrar o servidor.")
    print("=" * 70)
    
    # Executa o servidor de desenvolvimento:
    # NOTA DE COMPATIBILIDADE (Dash no Python 3.12+):
    #   - No Dash (>= 2.11 e Dash 3.x), o método oficial é 'app.run(...)'.
    #     O antigo método 'app.run_server()' foi descontinuado e gera ObsoleteAttributeException.
    #   - Caso execute em versões legadas antigas do Dash (< 2.11), mantemos fallback para 'app.run_server(...)'.
    #   - debug=True: habilita o Hot-Reloading (atualização automática ao salvar) e depurador de erros interativo.
    #   - host="0.0.0.0": escuta em todas as interfaces de rede locais (127.0.0.1 e IP da rede local).
    #   - port=8050: porta de comunicação padrão do Dash.
    try:
        app.run(debug=True, host="0.0.0.0", port=8050)
    except AttributeError:
        # Fallback para versões legadas do Dash (< 2.11)
        app.run_server(debug=True, host="0.0.0.0", port=8050)
