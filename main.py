import streamlit as st
import requests
import pandas as pd
import polars as pl
import plotly.express as px
from loguru import logger

st.set_page_config(layout="wide")


def formata_numero(valor, prefixo=""):
    for unidade in ["", "mil"]:
        if valor < 1000:
            return f"{prefixo} {valor:.2f} {unidade}"
        valor /= 1000
    return f"{prefixo} {valor:.2f} milhoes"


st.title("DASHBOARD DE VENDAS :rocket:")

url = "https://labdados.com/produtos"

regioes = ["Brasil", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]

st.sidebar.title("Filtros")
regiao = st.sidebar.selectbox("Região", regioes)

if regiao == "Brasil":
    regiao = ""

todos_anos = st.sidebar.checkbox("Dados de todo o periodo", value=True)

if todos_anos:
    ano = ""
else:
    ano = st.sidebar.slider("Ano", 2020, 2023)


@st.cache_data
def carregar_dados(url,query_string):
    response = requests.get(url, params=query_string)
    return pl.DataFrame(response.json())

query_string = {"regiao": regiao.lower(), "ano": ano}

#response = requests.get(url, params=query_string)
# logger.info(response.json()[0])
logger.info(query_string)
#dados = pl.DataFrame(response.json())
#dados_pd = pd.DataFrame.from_dict(response.json())

dados = carregar_dados(url,query_string)
dados_pd = carregar_dados(url,query_string).to_pandas()

dados = dados.with_columns(pl.col("Data da Compra").str.strptime(pl.Date, "%d/%m/%Y"))
dados_pd["Data da Compra"] = pd.to_datetime(
    dados_pd["Data da Compra"], format="%d/%m/%Y"
)

# o sort foi a chave para as coisas funcionarem
filtro_vendedores = st.sidebar.multiselect(
    "Vendedores", dados["Vendedor"].unique().sort(descending=False)
)
logger.info(filtro_vendedores)
if filtro_vendedores:
    dados = dados.filter(pl.col("Vendedor").is_in(filtro_vendedores))


# tabelas
receita_mensal = (
    dados_pd.set_index("Data da Compra")
    .groupby(pd.Grouper(freq="ME"))["Preço"]
    .sum()
    .reset_index()
)
receita_mensal_pl = (
    dados.sort("Data da Compra", descending=False)
    .group_by_dynamic(index_column="Data da Compra", every="1mo")
    .agg(pl.col("Preço").sum())
)

quantidade_mensal_pl = (
    dados.sort("Data da Compra", descending=False)
    .group_by_dynamic(index_column="Data da Compra", every="1mo")
    .agg(pl.col("Data da Compra").count().alias("Quantidade"))
)


receita_mensal["Ano"] = receita_mensal["Data da Compra"].dt.year
receita_mensal["Mes"] = receita_mensal["Data da Compra"].dt.month

receita_categorias = (
    dados.group_by("Categoria do Produto")
    .agg(pl.col("Preço").sum())
    .sort("Preço", descending=True)
)

##tabelas

receita_estados = (
    dados.group_by([pl.col("Local da compra"), pl.col("lat"), pl.col("lon")])
    .agg(pl.col("Preço").sum())
    .sort("Preço", descending=True)
)

receita_mensal_pl = receita_mensal_pl.with_columns(
    pl.col("Data da Compra").dt.year().alias("Ano"),
    pl.col("Data da Compra").dt.strftime("%B").alias("Mes"),
)

quantidade_mensal_pl = quantidade_mensal_pl.with_columns(
    pl.col("Data da Compra").dt.year().alias("Ano"),
    pl.col("Data da Compra").dt.strftime("%B").alias("Mes"),
)

# como seria no pandas
# receitas_estados = dados.groupby('Local da compra')[['Preço']].sum()
# receitas_estados = dados.drop_duplicates(subset='Local da compra')[['Local da compra','lat','lon']].merge(receita_estados, left_on = 'Local da compra', right_index = True)


# logger.info(receita_mensal_pl.max().to_pandas())
# logger.info(type(receita_mensal_pl.max().to_pandas()))
# logger.info(type(pl.DataFrame(receita_mensal_pl.max())))

### Tabelas de quantidade de vendas

quantidade_estados = (
    dados.group_by([pl.col("Local da compra"), pl.col("lat"), pl.col("lon")])
    .agg(pl.col("Local da compra").count().alias("Quantidade"))
    .sort("Quantidade", descending=True)
)

estados = dados.group_by("Local da compra").agg(
    pl.sum("Preço"), pl.count("Vendedor").alias("qtd")
)
estados = estados.rename({"Local da compra": "Estado"})

produtos = (
    dados.group_by("Categoria do Produto")
    .agg(pl.col("Categoria do Produto").count().alias("qtd"))
    .sort("qtd", descending=True)
)


### Tabelas vendedores
vendedores = dados.group_by("Vendedor").agg(
    pl.sum("Preço"), pl.count("Vendedor").alias("qtd")
)
# map emotions to a color
vd = dict(zip(vendedores["Vendedor"].unique(), px.colors.qualitative.G10))

## Graficos
fig_mapa_receita = px.scatter_geo(
    receita_estados,
    lat="lat",
    lon="lon",
    scope="south america",
    size="Preço",
    template="seaborn",
    hover_name="Local da compra",
    hover_data={"lat": False, "lon": False},
    title="Receita por estado",
)

fig_receita_mensal = px.line(
    receita_mensal_pl,
    x="Mes",
    y="Preço",
    markers=True,
    # Aqui o range_y pega os menores valores de todas as linhas aparentemente, o segundo parametro foi inserido como dataframe no pandas ou no
    range_y=(0, receita_mensal_pl.max().to_pandas()),
    color="Ano",
    line_dash="Ano",
    title="receita_mensal",
)

fig_receita_mensal.update_layout(yaxis_title="Receita")

fig_receita_estados = px.bar(
    receita_estados.head(),
    x="Local da compra",
    y="Preço",
    text_auto=True,
    title="Top 5 estados com maior receita",
)

fig_receita_estados.update_layout(yaxis_title="Receita")

fig_receita_categorias = px.bar(
    receita_categorias,
    x="Categoria do Produto",
    y="Preço",
    text_auto=True,
    title="Receita por categoria",
)

fig_receita_categorias.update_layout(yaxis_title="Receita")

### Figuras


fig_quantidade_estados = px.scatter_geo(
    quantidade_estados,
    lat="lat",
    lon="lon",
    scope="south america",
    size="Quantidade",
    template="seaborn",
    hover_name="Local da compra",
    hover_data={"lat": False, "lon": False},
    title="Quantidade por estado",
)

fig_quantidade_mensal = px.line(
    quantidade_mensal_pl,
    x="Mes",
    y="Quantidade",
    markers=True,
    # Aqui o range_y pega os menores valores de todas as linhas aparentemente, o segundo parametro foi inserido como dataframe no pandas ou no
    range_y=(0, quantidade_mensal_pl.max().to_pandas()),
    color="Ano",
    line_dash="Ano",
    title="receita_mensal",
)


## Visualizacao no streamlit
aba1, aba2, aba3 = st.tabs(["Receita", "Quantidade de vendas", "Vendendores"])

with aba1:
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Receita", formata_numero(dados["Preço"].sum(), "R$"), help="Receita total"
        )
        st.plotly_chart(fig_mapa_receita, use_container_width=True)
        st.plotly_chart(fig_receita_estados, use_container_width=True)
    with col2:
        st.metric("Quantidade de vendas", formata_numero(dados.shape[0]))
        st.plotly_chart(fig_receita_mensal, use_container_width=True)
        st.plotly_chart(fig_receita_categorias, use_container_width=True)

with aba2:
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Receita", formata_numero(dados["Preço"].sum(), "R$"), help="Receita total"
        )
        st.plotly_chart(fig_quantidade_estados)
        fig_quantidade_estados = px.bar(
            estados.sort(pl.col("qtd"), descending=True).head(),
            x="qtd",
            y="Estado",
            text_auto=True,
            title=f"Top 5 estados (quantidade de vendas)",
            color="Estado",
        )
        st.plotly_chart(fig_quantidade_estados)
    with col2:
        st.metric("Quantidade de vendas", formata_numero(dados.shape[0]))
        st.plotly_chart(fig_quantidade_mensal)
        fig_quantidade_produto = px.bar(
            produtos,
            x="Categoria do Produto",
            y="qtd",
            text_auto=True,
            title="Quantidade de produtos vendidos",
            color="Categoria do Produto",
        )
        st.plotly_chart(fig_quantidade_produto)


with aba3:
    qtd_vendedores = st.number_input("Quantidade de vendedores", 2, 10, 5)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Receita", formata_numero(dados["Preço"].sum(), "R$"), help="Receita total"
        )
        fig_receita_vendedores = px.bar(
            vendedores.sort(pl.col("qtd"), descending=False).head(qtd_vendedores),
            x="qtd",
            y="Vendedor",
            text_auto=True,
            title=f"Top {qtd_vendedores} vendedores (quantidade de vendas)",
            color="Vendedor",
            color_discrete_map=vd,
        )
        st.plotly_chart(fig_receita_vendedores)
    with col2:
        st.metric("Quantidade de vendas", formata_numero(dados.shape[0]))
        fig_receita_vendedores = px.bar(
            vendedores.sort(pl.col("Preço"), descending=False).head(qtd_vendedores),
            x="Preço",
            y="Vendedor",
            text_auto=True,
            title=f"Top {qtd_vendedores} vendedores (receita)",
            color="Vendedor",
            color_discrete_map=vd,
        )
        st.plotly_chart(fig_receita_vendedores)
# st.dataframe(dados)
