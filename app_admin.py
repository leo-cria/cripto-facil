import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Painel Admin - Cripto Fácil", layout="wide")

# --- Autenticação do Admin ---
def autenticar_admin():
    st.sidebar.title("🔐 Acesso do Administrador")
    senha = st.sidebar.text_input("Senha do Admin", type="password")
    return senha == st.secrets.get("admin_password", "admin123")

if not autenticar_admin():
    st.error("Acesso restrito! Informe a senha correta.")
    st.stop()

st.title("👨‍💼 Painel Administrativo - Cripto Fácil")

# --- Carregar dados CSV ---
USERS_FILE = "users.csv"
OPERACOES_FILE = "operacoes.csv"

df_usuarios = pd.read_csv(USERS_FILE, dtype=str) if os.path.exists(USERS_FILE) else pd.DataFrame()
df_ops = pd.read_csv(OPERACOES_FILE, dtype=str) if os.path.exists(OPERACOES_FILE) else pd.DataFrame()

if not df_ops.empty:
    df_ops['custo_total'] = pd.to_numeric(df_ops['custo_total'], errors='coerce')
    df_ops['data_operacao'] = pd.to_datetime(df_ops['data_operacao'], errors='coerce')

# --- Estatísticas ---
st.subheader("📊 Estatísticas Gerais")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Usuários", len(df_usuarios))
col2.metric("Operações", len(df_ops))
col3.metric("Hoje", datetime.today().strftime('%d/%m/%Y'))
col4.metric("Média Ops/Usuário", f"{(len(df_ops)/max(len(df_usuarios),1)):.1f}")

# --- Lista de Usuários ---
st.subheader("👥 Usuários Cadastrados")
if not df_usuarios.empty:
    st.dataframe(df_usuarios, use_container_width=True)
else:
    st.info("Nenhum usuário cadastrado.")

# --- Lista de Operações ---
st.subheader("💼 Operações Realizadas")
if not df_ops.empty:
    st.dataframe(df_ops, use_container_width=True)
else:
    st.info("Nenhuma operação registrada.")

# --- Gráfico: Volume por Mês ---
if not df_ops.empty:
    st.subheader("📈 Volume Total Movimentado por Mês")
    df_ops['mes'] = df_ops['data_operacao'].dt.to_period("M").astype(str)
    df_mes = df_ops.groupby("mes")["custo_total"].sum().reset_index()
    fig = px.bar(df_mes, x="mes", y="custo_total", title="Volume movimentado (R$)", labels={"mes": "Mês", "custo_total": "Valor"})
    st.plotly_chart(fig, use_container_width=True)

# --- Gráfico: Criptomoedas mais usadas ---
if 'cripto' in df_ops.columns:
    st.subheader("🔥 Criptomoedas mais negociadas")
    df_top = df_ops['cripto'].value_counts().reset_index()
    df_top.columns = ['Cripto', 'Total de Operações']
    fig2 = px.pie(df_top, names="Cripto", values="Total de Operações", hole=0.3)
    st.plotly_chart(fig2, use_container_width=True)

# --- Ranking dos usuários por volume movimentado ---
st.subheader("🏆 Ranking de Usuários por Volume")
if not df_ops.empty and 'cpf_usuario' in df_ops.columns:
    ranking = df_ops.groupby("cpf_usuario")["custo_total"].sum().reset_index()
    ranking = ranking.sort_values(by="custo_total", ascending=False).reset_index(drop=True)
    ranking.index += 1
    ranking.columns = ["CPF do Usuário", "Valor Total (R$)"]
    st.dataframe(ranking, use_container_width=True)

# --- Exportar dados ---
st.subheader("📥 Exportar Dados CSV")
col5, col6 = st.columns(2)
if col5.button("⬇️ Exportar Usuários"):
    st.download_button("Download usuários.csv", df_usuarios.to_csv(index=False), file_name="usuarios.csv")

if col6.button("⬇️ Exportar Operações"):
    st.download_button("Download operacoes.csv", df_ops.to_csv(index=False), file_name="operacoes.csv")

# --- Rodapé ---
st.markdown("---")
st.caption("🔒 Acesso restrito ao administrador | Cripto Fácil © 2025")
