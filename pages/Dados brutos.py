import streamlit as st
import requests
import pandas as pd
import polars as pl
from loguru import logger as log
import time


#evita que a funcao rode a leitura de dados mais uma vez e guarda no cache
@st.cache_data
def converte_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def mensagem_sucesso():
    sucesso = st.success("Arquivo CSV baixado com sucesso!", icon="✅")
    time.sleep(5)
    sucesso.empty()


st.title("Dados Brutos")

url = "https://labdados.com/produtos"


@st.cache_data
def carregar_dados(url):
    response = requests.get(url)
    return pl.DataFrame(response.json())


dados = carregar_dados(url)
dados = dados.with_columns(
    pl.col("Data da Compra").str.strptime(pl.Date, "%d/%m/%Y"),
)

with st.expander("Colunas"):
    colunas = st.multiselect(
        "Selecione as colunas para exibir",
        list(dados.columns),
        default=list(dados.columns),
    )

st.sidebar.title("Filtros")
with st.sidebar.expander("Nome do produto"):
    produtos = st.multiselect(
        "Selecione os produtos",
        dados["Produto"].unique().sort(descending=False),
        default=dados["Produto"].unique().sort(descending=False),
    )

with st.sidebar.expander("Preço do produto"):
    preco = st.slider("Selecione o preço", 0, 5000, (0, 5000))

with st.sidebar.expander("Data da Compra"):
    data_compra = st.date_input(
        "Selecione a data da compra",
        (dados["Data da Compra"].min(), dados["Data da Compra"].max()),
    )

with st.sidebar.expander("Categoria do produto"):
    categoria = st.multiselect(
        "Selecione as categorias",
        dados["Categoria do Produto"].unique().sort(descending=False),
        dados["Categoria do Produto"].unique().sort(descending=False),
    )
with st.sidebar.expander("Frete da venda"):
    frete = st.slider("Frete", 0, 250, (0, 250))
with st.sidebar.expander("Vendedor"):
    vendedores = st.multiselect(
        "Selecione os vendedores",
        dados["Vendedor"].unique().sort(descending=False),
        dados["Vendedor"].unique().sort(descending=False),
    )
with st.sidebar.expander("Local da compra"):
    local_compra = st.multiselect(
        "Selecione o local da compra",
        dados["Local da compra"].unique().sort(descending=False),
        dados["Local da compra"].unique().sort(descending=False),
    )
with st.sidebar.expander("Avaliação da compra"):
    avaliacao = st.slider("Selecione a avaliação da compra", 1, 5, value=(1, 5))
with st.sidebar.expander("Tipo de pagamento"):
    tipo_pagamento = st.multiselect(
        "Selecione o tipo de pagamento",
        dados["Tipo de pagamento"].unique().sort(descending=False),
        dados["Tipo de pagamento"].unique().sort(descending=False),
    )
with st.sidebar.expander("Quantidade de parcelas"):
    qtd_parcelas = st.slider("Selecione a quantidade de parcelas", 1, 24, (1, 24))

log.info(f"Produtos selecionados: {produtos}")
log.info("--------------------------------------------------")
log.info(f"Data da compra selecionada: {data_compra}")
log.info("--------------------------------------------------")
log.info(f"Preço selecionado: {preco}")


# mutiselect entrar como nome da coluna in @nome da variavel et slider entrar como um entre @variavel[0] <= <= @variavel[1]
query = """
Produto in @produtos and \
`Categoria do Produto` in @categoria and \
@preco[0] <= Preço <= @preco[1] and \
@frete[0] <= Frete <= @frete[1] and \
@data_compra[0] <= `Data da Compra` <= @data_compra[1] and \
Vendedor in @vendedores and \
`Local da compra` in @local_compra and \
@avaliacao[0]<= `Avaliação da compra` <= @avaliacao[1] and \
`Tipo de pagamento` in @tipo_pagamento and \
@qtd_parcelas[0] <= `Quantidade de parcelas` <= @qtd_parcelas[1]
"""

dados_filtrados = dados.to_pandas().query(query)
dados_filtrados = dados_filtrados[colunas]

filter_multiselect = {
    "Produto": produtos,
    "Categoria do Produto": categoria,
    "Vendedor": vendedores,
    "Local da compra": local_compra,
    "Tipo de pagamento": tipo_pagamento,
}

filter_slider = {
    "Preço": preco,
    "Frete": frete,
    "Avaliação da compra": avaliacao,
    "Quantidade de parcelas": qtd_parcelas,
}


log.info(dados.head(1))
"""if produtos:
    dados = dados.filter(pl.col('Produto').is_in(produtos))
if preco:
    dados = dados.filter(pl.col('Preço').is_between(preco[0],preco[1]))"""
"""for f, filter in filter_slider.items():
    if filter:
        dados = dados.filter(pl.col(f).is_between(filter[0], filter[1]))

for f, filter in filter_multiselect.items():
    if filter:
        dados = dados.filter(pl.col(f).is_in(filter))"""


"""if data_compra.__len__() == 2:
    dados = dados.filter(pl.col("Data da Compra").is_between(data_compra[0], data_compra[1]))
if colunas:
    dados = dados.select(colunas)"""


st.metric("Linhas", dados_filtrados.shape[0])
st.dataframe(dados_filtrados)
st.markdown(
    f"A tabela possui :blue[{dados_filtrados.shape[0]}] linhas e :blue[{dados_filtrados.shape[1]}] colunas"
)

st.markdown("Escreva um nome para o arquivo")
coluna1, coluna2 = st.columns(2)
with coluna1:
    nome_arquivo = st.text_input("", label_visibility="collapsed", value="dados")
    nome_arquivo += ".csv"
with coluna2:
    st.download_button(
        "Fazer o download da tabela csv",
        data=converte_csv(dados_filtrados),
        file_name=nome_arquivo,
        mime="text/csv",
        on_click=mensagem_sucesso,
    )
