import streamlit as st
import pandas as pd
import hashlib
import os
import random
import string
import uuid
from datetime import datetime
import time
import json # ESSENCIAL: Importa a biblioteca JSON

# Configuração inicial da página Streamlit
st.set_page_config(page_title="Cripto Fácil", page_icon="🟧₿", layout="wide")

# Definição dos nomes dos arquivos para armazenar dados de usuários, carteiras e operações
USERS_FILE = "users.csv"
CARTEIRAS_FILE = "carteiras.csv"
OPERACOES_FILE = "operacoes.csv"
CRYPTOS_FILE = "cryptos.json" # Caminho para o arquivo JSON das criptomoedas

# --- Funções Utilitárias para Manipulação de Dados ---

def load_users():
    """
    Carrega os dados dos usuários do arquivo CSV.
    Cria um DataFrame vazio se o arquivo não existir.
    """
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE, dtype=str)
    return pd.DataFrame(columns=["cpf", "name", "phone", "email", "password_hash"])

def save_users(df):
    """Salva o DataFrame de usuários no arquivo CSV."""
    df.to_csv(USERS_FILE, index=False)

def hash_password(password):
    """Gera um hash SHA256 da senha fornecida para armazenamento seguro."""
    return hashlib.sha256(password.encode()).hexdigest()

def send_recovery_code(email):
    """
    Simula o envio de um código de recuperação para o e-mail do usuário.
    Armazena o código e o e-mail na sessão para verificação posterior.
    """
    code = "".join(random.choices(string.digits, k=6))
    st.session_state["recovery_code"] = code
    st.session_state["reset_email"] = email
    st.success(f"Código enviado para {email} 🔐 (simulado: **{code}**)")

def load_carteiras():
    """
    Carrega os dados das carteiras do arquivo CSV.
    Adiciona a coluna 'cpf_usuario' se não existir para compatibilidade.
    Cria um DataFrame vazio se o arquivo não existir.
    """
    if os.path.exists(CARTEIRAS_FILE):
        df = pd.read_csv(CARTEIRAS_FILE, dtype=str)
        if 'cpf_usuario' not in df.columns:
            df['cpf_usuario'] = ""
        return df
    return pd.DataFrame(columns=["id", "tipo", "nome", "nacional", "info1", "info2", "cpf_usuario"])

def save_carteiras(df):
    """Salva o DataFrame de carteiras no arquivo CSV."""
    df.to_csv(CARTEIRAS_FILE, index=False)

def load_operacoes():
    """
    Carrega os dados das operações do arquivo CSV.
    Cria um DataFrame vazio se o arquivo não existir.
    Garante que 'quantidade', 'custo_total', 'preco_medio_compra_na_op', 'lucro_prejuizo_na_op'
    sejam numéricos e que 'data_operacao' seja datetime.
    Adiciona novas colunas se não existirem (para compatibilidade com CSVs antigos).
    """
    if os.path.exists(OPERACOES_FILE):
        df = pd.read_csv(OPERACOES_FILE, dtype=str)

        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
        df['custo_total'] = pd.to_numeric(df['custo_total'], errors='coerce')

        if 'preco_medio_compra_na_op' not in df.columns:
            df['preco_medio_compra_na_op'] = float('nan')
        else:
            df['preco_medio_compra_na_op'] = pd.to_numeric(df['preco_medio_compra_na_op'], errors='coerce')

        if 'lucro_prejuizo_na_op' not in df.columns:
            df['lucro_prejuizo_na_op'] = float('nan')
        else:
            df['lucro_prejuizo_na_op'] = pd.to_numeric(df['lucro_prejuizo_na_op'], errors='coerce')

        # Adiciona a nova coluna 'ptax_na_op' se não existir
        if 'ptax_na_op' not in df.columns:
            df['ptax_na_op'] = float('nan')
        else:
            df['ptax_na_op'] = pd.to_numeric(df['ptax_na_op'], errors='coerce')


        df['data_operacao'] = pd.to_datetime(df['data_operacao'], errors='coerce')
        return df
    return pd.DataFrame(columns=[
        "id", "wallet_id", "cpf_usuario", "tipo_operacao", "cripto",
        "quantidade", "custo_total", "data_operacao",
        "preco_medio_compra_na_op",
        "lucro_prejuizo_na_op",
        "ptax_na_op" # Adicionada nova coluna
    ])

def save_operacoes(df):
    """Salva o DataFrame de operações no arquivo CSV."""
    df['data_operacao'] = df['data_operacao'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(OPERACOES_FILE, index=False)

# --- FUNÇÃO PRINCIPAL QUE LÊ O ARQUIVO JSON ---
@st.cache_data
def load_cryptocurrencies_from_file():
    """
    Carrega a lista de criptomoedas de um arquivo JSON local.
    Retorna uma lista vazia se o arquivo não existir ou houver erro.
    """
    if os.path.exists(CRYPTOS_FILE):
        try:
            with open(CRYPTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error(f"Erro ao decodificar o arquivo {CRYPTOS_FILE}. Verifique o formato JSON.")
            return []
    else:
        # Se o arquivo não existir, forneça uma lista padrão ou avise.
        st.warning(f"Arquivo '{CRYPTOS_FILE}' não encontrado. Usando uma lista de criptomoedas padrão.")
        # Esta lista padrão é um fallback caso o JSON não seja encontrado ou esteja vazio.
        return ["BTC - Bitcoin", "ETH - Ethereum", "SOL - Solana", "ADA - Cardano", "XRP - Ripple", "BNB - Binance Coin", "DOGE - Dogecoin", "SHIB - Shiba Inu", "DOT - Polkadot", "MATIC - Polygon"]


# --- Funções para Exibição do Dashboard ---
def show_dashboard():
    """
    Exibe o dashboard principal da aplicação.
    """
    with st.sidebar:
        st.markdown("<h3 style='text-align:center;'>🟧₿ Cripto Fácil</h3><hr>", unsafe_allow_html=True)

        pages = {
            "Portfólio": "🚀 Meu Portfólio",
            "Minha Conta": "👤 Minha Conta",
            "Carteiras": "🗂️ Minhas Carteiras",
            "Relatórios": "🗃️ Relatórios Detalhados",
            "Imposto de Renda": "🏛️ Declaração de IR",
            "Detalhes da Carteira": "📂 Detalhes da Carteira e Operações"
        }

        # Removendo "Operações" do menu lateral
        for page_name in ["Portfólio", "Minha Conta", "Carteiras", "Relatórios", "Imposto de Renda"]:
            if st.button(page_name, key=f"sidebar_btn_{page_name.lower().replace(' ', '_')}"):
                st.session_state["pagina_atual"] = page_name
                st.session_state["accessed_wallet_id"] = None
                st.session_state["confirm_delete_wallet_id"] = None
                st.session_state["confirm_delete_operation_id"] = None
                st.rerun()

        st.markdown("---")
        if st.button("🔒 Sair"):
            st.session_state["logged_in"] = False
            st.session_state["auth_page"] = "login"
            st.session_state["pagina_atual"] = "Portfólio"
            st.session_state["accessed_wallet_id"] = None
            st.session_state["confirm_delete_wallet_id"] = None
            st.session_state["confirm_delete_operation_id"] = None
            st.rerun()

    page = st.session_state.get("pagina_atual", "Portfólio")
    # Título da página dinâmico
    st.title(pages[page])

    if page == "Minha Conta":
        df = load_users()
        usuario = df[df['cpf'] == st.session_state["cpf"]].iloc[0]
        with st.form("form_account"):
            st.text_input("Nome", value=usuario['name'], disabled=True)
            st.text_input("CPF", value=usuario['cpf'], disabled=True)
            phone = st.text_input("Telefone", value=usuario['phone'])
            email = st.text_input("Email", value=usuario['email'])
            submitted = st.form_submit_button("Salvar alterações ✅")
            if submitted:
                df.loc[df['cpf'] == usuario['cpf'], ['phone', 'email']] = phone, email
                save_users(df)
                st.success("Dados atualizados!")

        with st.expander("Alterar senha"):
            with st.form("form_password"):
                atual = st.text_input("Senha atual", type="password")
                nova = st.text_input("Nova senha", type="password")
                confirmar = st.text_input("Confirme a senha", type="password")
                ok = st.form_submit_button("Alterar senha 🔑")
                if ok:
                    if hash_password(atual) != usuario['password_hash']:
                        st.error("Senha atual incorreta.")
                    elif nova != confirmar:
                        st.error("Nova senha não confere.")
                    else:
                        df.loc[df['cpf'] == usuario['cpf'], 'password_hash'] = hash_password(nova)
                        save_users(df)
                        st.success("Senha alterada com sucesso!")

    elif page == "Carteiras":
        df_carteiras = load_carteiras()
        user_cpf = st.session_state["cpf"]
        user_carteiras_df = df_carteiras[df_carteiras['cpf_usuario'] == user_cpf].copy()

        st.markdown("""
            <div style='border:2px solid #e0e0e0; border-radius:10px; padding:20px; background-color:#fafafa;'>
                <h3 style='margin-top:0;'>Criar nova carteira</h3>
            </div>
        """, unsafe_allow_html=True)

        tipo_selecionado_criar = st.radio(
            "Tipo de carteira",
            ["Auto Custódia", "Corretora"],
            key="tipo_carteira_selection_global_criar",
            horizontal=True
        )

        with st.form("form_add_carteira"):
            nome_input_criar = ""
            info1_input_criar = ""
            info2_input_criar = ""

            if tipo_selecionado_criar == "Auto Custódia":
                nome_input_criar = st.selectbox("Rede", ["ETHEREUM", "SOLANA", "BITCOIN", "BASE"], key="rede_selector_criar")
                info1_input_criar = st.text_input("Endereço da carteira", key="endereco_field_criar")
            else: # Corretora
                nome_input_criar = st.selectbox("Corretora", ["BINANCE", "BYBIT", "COINBASE", "OKX", "MEXC", "MERCADO BITCOIN"], key="corretora_selector_criar")
                pass

            nacional_input_criar = st.radio("Origem da carteira:", ["Nacional", "Estrangeira"], key="nacionalidade_radio_field_criar")

            enviado_criar = st.form_submit_button("Criar carteira ➕")
            if enviado_criar:
                if tipo_selecionado_criar == "Auto Custódia" and (not nome_input_criar or not info1_input_criar):
                    st.error("Por favor, preencha todos os campos obrigatórios para Auto Custódia.")
                elif tipo_selecionado_criar == "Corretora" and not nome_input_criar:
                    st.error("Por favor, selecione uma corretora.")
                else:
                    nova_carteira = pd.DataFrame([{
                        "id": f"carteira_{uuid.uuid4()}",
                        "tipo": tipo_selecionado_criar,
                        "nome": nome_input_criar,
                        "nacional": nacional_input_criar,
                        "info1": info1_input_criar,
                        "info2": info2_input_criar,
                        "cpf_usuario": user_cpf
                    }])
                    current_carteiras_df = load_carteiras()
                    save_carteiras(pd.concat([current_carteiras_df, nova_carteira], ignore_index=True))
                    st.success("Carteira criada com sucesso!")
                    st.rerun()

        st.subheader("Minhas carteiras")
        if not user_carteiras_df.empty:
            for _, row in user_carteiras_df.iterrows():
                with st.expander(f"🔗 {row['nome']} ({row['tipo']}) - Origem: {row['nacional']}", expanded=False):
                    st.write(f"**Tipo:** {row['tipo']}")
                    st.write(f"**Origem:** {row['nacional']}")

                    if row['tipo'] == 'Auto Custódia' and str(row['info1']).strip().lower() != 'nan' and str(row['info1']).strip() != '':
                        st.write(f"**Endereço da Carteira:** {row['info1']}")
                    elif row['tipo'] == 'Corretora':
                        if str(row['info1']).strip().lower() != 'nan' and str(row['info1']).strip() != '':
                            st.write(f"**API Key (Antiga):** {row['info1']}")
                        if str(row['info2']).strip().lower() != 'nan' and str(row['info2']).strip() != '':
                            st.write(f"**Secret Key (Antiga):** {row['info2']}")

                    col_access, col_delete = st.columns(2)

                    with col_access:
                        if st.button(f"Acessar Carteira ➡️", key=f"access_carteira_btn_{row['id']}"):
                            st.session_state["accessed_wallet_id"] = row['id']
                            st.session_state["pagina_atual"] = "Detalhes da Carteira"
                            st.session_state["confirm_delete_wallet_id"] = None
                            st.session_state["confirm_delete_operation_id"] = None
                            st.rerun()

                    with col_delete:
                        if st.button(f"🗑️ Excluir", key=f"delete_carteira_btn_{row['id']}"):
                            st.session_state['confirm_delete_wallet_id'] = row['id']
                            st.rerun()

        else:
            st.info("Nenhuma carteira cadastrada ainda para este usuário.")

        wallet_confirm_placeholder = st.empty()
        if st.session_state.get('confirm_delete_wallet_id'):
            with wallet_confirm_placeholder.container():
                wallet_to_confirm_delete_id = st.session_state['confirm_delete_wallet_id']
                wallet_name = df_carteiras[df_carteiras['id'] == wallet_to_confirm_delete_id]['nome'].iloc[0]

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Carteira</h4>
                    <p>Tem certeza que deseja excluir a carteira <strong>"{wallet_name}"</strong>?</p>
                    <p style="color:#ff0000; font-weight:bold;">Isso também excluirá TODAS as operações associadas a ela!</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_wallet, col_cancel_wallet = st.columns([0.2, 0.8])
                with col_confirm_wallet:
                    if st.button("Sim, Excluir", key="confirm_wallet_delete_btn_modal"):
                        df_carteiras_updated = df_carteiras[df_carteiras['id'] != wallet_to_confirm_delete_id]
                        save_carteiras(df_carteiras_updated)

                        df_operacoes_current = load_operacoes()
                        df_operacoes_updated = df_operacoes_current[df_operacoes_current['wallet_id'] != wallet_to_confirm_delete_id]
                        save_operacoes(df_operacoes_updated)

                        st.success(f"Carteira '{wallet_name}' e suas operações excluídas com sucesso!")
                        st.session_state['confirm_delete_wallet_id'] = None
                        wallet_confirm_placeholder.empty()
                        st.rerun()
                with col_cancel_wallet:
                    if st.button("Cancelar", key="cancel_wallet_delete_btn_modal"):
                        st.session_state['confirm_delete_wallet_id'] = None
                        wallet_confirm_placeholder.empty()
                        st.rerun()
        else:
            wallet_confirm_placeholder.empty()

    elif page == "Detalhes da Carteira":
        show_wallet_details()

    else:
        st.write(f"(Conteúdo da página: **{page}**) ✨")

# --- Nova Página: Detalhes da Carteira e Operações ---
def show_wallet_details():
    """
    Exibe os detalhes de uma carteira específica e permite o registro de operações.
    Também exibe o portfólio consolidado da carteira com métricas e um gráfico.
    """
    wallet_id = st.session_state.get("accessed_wallet_id")
    if not wallet_id:
        st.warning("Nenhuma carteira selecionada. Por favor, acesse uma carteira pela página 'Minhas Carteiras'.")
        return

    df_carteiras = load_carteiras()
    current_wallet = df_carteiras[df_carteiras['id'] == wallet_id].iloc[0]
    user_cpf = st.session_state["cpf"]

    is_foreign_wallet = (current_wallet['nacional'] == 'Estrangeira')

    st.subheader(f"Carteira: {current_wallet['nome']} ({current_wallet['tipo']})")
    st.write(f"**ID da Carteira:** {current_wallet['id']}")
    st.write(f"**Origem:** {current_wallet['nacional']}")

    if current_wallet['tipo'] == 'Auto Custódia' and str(current_wallet['info1']).strip().lower() != 'nan' and str(current_wallet['info1']).strip() != '':
        st.write(f"**Endereço da Carteira:** {current_wallet['info1']}")
    elif current_wallet['tipo'] == 'Corretora':
        if str(current_wallet['info1']).strip().lower() != 'nan' and str(current_wallet['info1']).strip() != '':
            st.write(f"**API Key (Antiga):** {current_wallet['info1']}")
        if str(current_wallet['info2']).strip().lower() != 'nan' and str(current_wallet['info2']).strip() != '':
            st.write(f"**Secret Key (Antiga):** {current_wallet['info2']}")

    st.markdown("---")

    # --- Seção do Portfólio Consolidado da Carteira ---
    st.markdown("#### Portfólio Consolidado da Carteira")

    df_operacoes_portfolio = load_operacoes()
    wallet_ops_for_portfolio = df_operacoes_portfolio[
        (df_operacoes_portfolio['wallet_id'] == wallet_id) &
        (df_operacoes_portfolio['cpf_usuario'] == user_cpf)
    ].copy()

    total_lucro_realizado = 0.0

    portfolio_detail = {}

    if not wallet_ops_for_portfolio.empty:
        # Calcular Lucro Realizado da Carteira (soma de lucro_prejuizo_na_op de vendas)
        vendas_realizadas_totais = wallet_ops_for_portfolio[
            (wallet_ops_for_portfolio['tipo_operacao'] == 'Venda') &
            (pd.notna(wallet_ops_for_portfolio['lucro_prejuizo_na_op']))
        ]
        if not vendas_realizadas_totais.empty:
            total_lucro_realizado = vendas_realizadas_totais['lucro_prejuizo_na_op'].sum()

        # --- Calcular detalhes do portfólio atual por cripto ---
        for cripto_simbolo in wallet_ops_for_portfolio['cripto'].unique():
            ops_cripto = wallet_ops_for_portfolio[wallet_ops_for_portfolio['cripto'] == cripto_simbolo]

            qtd_comprada = ops_cripto[ops_cripto['tipo_operacao'] == 'Compra']['quantidade'].sum()
            qtd_vendida = ops_cripto[ops_cripto['tipo_operacao'] == 'Venda']['quantidade'].sum()
            quantidade_atual = qtd_comprada - qtd_vendida

            if quantidade_atual > 0:
                total_custo_comprado = ops_cripto[ops_cripto['tipo_operacao'] == 'Compra']['custo_total'].sum()

                total_custo_base_vendido = 0
                vendas_da_cripto = ops_cripto[ops_cripto['tipo_operacao'] == 'Venda']
                if not vendas_da_cripto.empty:
                    # O custo base vendido é a quantidade vendida vezes o preço médio de compra na operação
                    total_custo_base_vendido = (vendas_da_cripto['quantidade'] * vendas_da_cripto['preco_medio_compra_na_op']).sum()

                # Custo total das unidades remanescentes na carteira
                custo_total_atual_estimado = total_custo_comprado - total_custo_base_vendido

                if quantidade_atual > 0:
                    custo_medio = custo_total_atual_estimado / quantidade_atual
                else:
                    custo_medio = 0

                lucro_realizado_cripto = ops_cripto[
                    (ops_cripto['tipo_operacao'] == 'Venda') &
                    (pd.notna(ops_cripto['lucro_prejuizo_na_op']))
                ]['lucro_prejuizo_na_op'].sum()

                portfolio_detail[cripto_simbolo] = {
                    'quantidade': float(quantidade_atual), # Garante que é float
                    'custo_total': float(custo_total_atual_estimado), # Garante que é float
                    'custo_medio': float(custo_medio), # Garante que é float
                    'lucro_realizado': float(lucro_realizado_cripto) # Garante que é float
                }

    # Criar DataFrame para o portfólio detalhado
    portfolio_df = pd.DataFrame.from_dict(portfolio_detail, orient='index').reset_index()
    if not portfolio_df.empty:
        portfolio_df.columns = ['Cripto', 'Quantidade', 'Custo Total', 'Custo Médio', 'Lucro Realizado']
        portfolio_df = portfolio_df[portfolio_df['Quantidade'] > 0] # Filtrar só as que tem saldo > 0

        # Calcular o Custo Total da Carteira com base no portfolio_df filtrado
        total_custo_carteira_atualizado = portfolio_df['Custo Total'].sum()
    else:
        total_custo_carteira_atualizado = 0.0

    # Exibir as métricas em texto
    col_custo, col_lucro = st.columns(2)
    with col_custo:
        st.metric(label="Custo Total da Carteira (Ativo)", value=f"R$ {total_custo_carteira_atualizado:,.2f}")
    with col_lucro:
        st.metric(label="Lucro Realizado Total da Carteira", value=f"R$ {total_lucro_realizado:,.2f}")


    st.markdown("---")
    st.markdown("#### Portfolio Atual Detalhado")
    if not portfolio_df.empty:
        # Ordenar por 'Custo Total' em ordem decrescente
        portfolio_df = portfolio_df.sort_values(by='Custo Total', ascending=False)

        col_names_portfolio = ["Cripto", "Quantidade", "Custo Total", "Custo Médio", "Lucro Realizado"]
        cols_ratio_portfolio = [0.15, 0.20, 0.20, 0.20, 0.25]

        cols_portfolio = st.columns(cols_ratio_portfolio)
        for i, col_name in enumerate(col_names_portfolio):
            with cols_portfolio[i]:
                st.markdown(f"**{col_name}**")
        st.markdown("---")

        for idx, row in portfolio_df.iterrows():
            cols_portfolio = st.columns(cols_ratio_portfolio)
            with cols_portfolio[0]:
                st.write(row['Cripto'])
            with cols_portfolio[1]:
                # Exibir quantidade com 8 casas decimais
                st.write(f"{row['Quantidade']:.8f}")
            with cols_portfolio[2]:
                st.write(f"R$ {row['Custo Total']:.2f}")
            with cols_portfolio[3]:
                st.write(f"R$ {row['Custo Médio']:.2f}")
            with cols_portfolio[4]:
                color = "green" if row['Lucro Realizado'] >= 0 else "red"
                st.markdown(f"<span style='color:{color}'>R$ {row['Lucro Realizado']:.2f}</span>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("Sua carteira não possui criptomoedas atualmente (todas as compras foram compensadas por vendas).")


    st.markdown("---")

    st.markdown("#### Cadastrar Nova Operação")

    if 'current_tipo_operacao' not in st.session_state:
        st.session_state['current_tipo_operacao'] = "Compra"

    def update_op_type():
        st.session_state['current_tipo_operacao'] = st.session_state['tipo_op_radio_external']

    tipo_operacao_display = st.radio(
        "Tipo de Operação",
        ["Compra", "Venda"],
        horizontal=True,
        key="tipo_op_radio_external",
        on_change=update_op_type,
        index=["Compra", "Venda"].index(st.session_state['current_tipo_operacao'])
    )

    with st.form("form_nova_operacao"):
        current_op_type = st.session_state['current_tipo_operacao']

        # AQUI É ONDE SEU APP LÊ A LISTA DE CRIPTOMOEDAS DO JSON!
        cryptocurrencies = load_cryptocurrencies_from_file()
        cripto = st.selectbox("Criptomoeda", options=cryptocurrencies, key="cripto_select")

        # Campo de quantidade para garantir tratamento decimal
        quantidade = st.number_input("Quantidade", min_value=0.00000001, format="%.8f", key="quantidade_input")

        valor_label_base = ""
        if is_foreign_wallet:
            valor_label_base = "Custo Total (em USDT)" if current_op_type == "Compra" else "Total da Venda (em USDT)"
        else:
            valor_label_base = "Custo Total (em BRL)" if current_op_type == "Compra" else "Total da Venda (em BRL)"

        custo_total_input = st.number_input(valor_label_base, min_value=0.01, format="%.2f", key="custo_total_input")

        ptax_input = 1.0 # Default para carteiras nacionais, ou se não for informada
        valor_em_brl_preview = 0.0

        if is_foreign_wallet:
            ptax_input = st.number_input(
                "Taxa PTAX (BRL por USDT)",
                min_value=0.01,
                format="%.4f",
                value=5.00, # Valor padrão para teste, pode ser alterado
                key="ptax_input"
            )
        else:
            valor_em_brl_preview = custo_total_input


        data_operacao = st.date_input("Data da Operação", value="today", key="data_op_input")
        hora_operacao = st.time_input("Hora da Operação", value=datetime.now().time(), key="hora_op_input")

        submitted_op = st.form_submit_button("Registrar Operação ✅")

        if submitted_op:
            if not cripto or quantidade <= 0 or custo_total_input <= 0:
                st.error("Por favor, preencha todos os campos da operação corretamente.")
            elif is_foreign_wallet and ptax_input <= 0:
                st.error("Por favor, informe uma taxa PTAX válida para carteiras estrangeiras.")
            else:
                data_hora_completa = datetime.combine(data_operacao, hora_operacao)

                df_operacoes_existentes = load_operacoes()

                preco_medio_compra_na_op = float('nan')
                lucro_prejuizo_na_op = float('nan')

                custo_total_final_brl = custo_total_input * ptax_input # Já está em BRL se for nacional, ou convertido se for estrangeira

                # Lógica para cálculo de preço médio e lucro/prejuízo
                if current_op_type == 'Compra':
                    # Para compra, o preço médio na operação é o custo total dividido pela quantidade
                    preco_medio_compra_na_op = custo_total_input / quantidade
                    # lucro_prejuizo_na_op permanece NaN para compras
                elif current_op_type == 'Venda':
                    # Para vendas, precisamos calcular o lucro/prejuízo
                    # Pegar as operações de compra anteriores para a mesma cripto nesta carteira
                    compras_anteriores = df_operacoes_existentes[
                        (df_operacoes_existentes['wallet_id'] == wallet_id) &
                        (df_operacoes_existentes['cpf_usuario'] == user_cpf) &
                        (df_operacoes_existentes['cripto'] == cripto) &
                        (df_operacoes_existentes['tipo_operacao'] == 'Compra')
                    ].copy()

                    # Calcular o total de cripto ainda em posse para esta carteira/cripto
                    qtd_comprada_anterior = compras_anteriores['quantidade'].sum()
                    vendas_anteriores = df_operacoes_existentes[
                        (df_operacoes_existentes['wallet_id'] == wallet_id) &
                        (df_operacoes_existentes['cpf_usuario'] == user_cpf) &
                        (df_operacoes_existentes['tipo_operacao'] == 'Venda')
                    ].copy()
                    qtd_vendida_anterior = vendas_anteriores['quantidade'].sum()
                    saldo_atual_cripto = qtd_comprada_anterior - qtd_vendida_anterior

                    if quantidade > saldo_atual_cripto:
                        st.error(f"Quantidade de venda ({quantidade:.8f}) excede o saldo disponível ({saldo_atual_cripto:.8f}) para {cripto}. Saldo deve ser maior ou igual a zero.")
                        return # Impede o registro se a quantidade for maior que o saldo

                    # Calcular o preço médio de compra ponderado para o saldo restante
                    custo_total_compras = compras_anteriores['custo_total'].sum()
                    if qtd_comprada_anterior > 0:
                        preco_medio_ponderado_total = custo_total_compras / qtd_comprada_anterior
                    else:
                        preco_medio_ponderado_total = 0 # Não há compras para calcular preço médio

                    # Calcular o lucro/prejuízo
                    # Lucro/Prejuízo = (Quantidade Vendida * Preço de Venda por unidade) - (Quantidade Vendida * Preço Médio de Compra)
                    preco_por_unidade_venda = custo_total_input / quantidade
                    lucro_prejuizo_na_op = (quantidade * preco_por_unidade_venda) - (quantidade * preco_medio_ponderado_total)

                    preco_medio_compra_na_op = preco_medio_ponderado_total # Para registrar o preço médio na data da venda

                nova_operacao = pd.DataFrame([{
                    "id": f"op_{uuid.uuid4()}",
                    "wallet_id": wallet_id,
                    "cpf_usuario": user_cpf,
                    "tipo_operacao": current_op_type,
                    "cripto": cripto,
                    "quantidade": quantidade,
                    "custo_total": custo_total_final_brl, # Sempre em BRL
                    "data_operacao": data_hora_completa,
                    "preco_medio_compra_na_op": preco_medio_compra_na_op,
                    "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                    "ptax_na_op": ptax_input # Salva o PTAX usado na operação (se for estrangeira)
                }])
                save_operacoes(pd.concat([df_operacoes_existentes, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações")
    df_operacoes_historico = load_operacoes()
    wallet_ops_historico = df_operacoes_historico[
        (df_operacoes_historico['wallet_id'] == wallet_id) &
        (df_operacoes_historico['cpf_usuario'] == user_cpf)
    ].sort_values(by='data_operacao', ascending=False).copy()

    if not wallet_ops_historico.empty:
        # Renomear colunas para exibição amigável
        display_df = wallet_ops_historico.rename(columns={
            "tipo_operacao": "Tipo",
            "cripto": "Cripto",
            "quantidade": "Quantidade",
            "custo_total": "Custo/Valor Total (BRL)",
            "data_operacao": "Data da Operação",
            "preco_medio_compra_na_op": "Preço Médio Compra na Op.",
            "lucro_prejuizo_na_op": "Lucro/Prejuízo na Op.",
            "ptax_na_op": "PTAX na Op."
        })

        # Formatar colunas numéricas para exibição
        display_df['Quantidade'] = display_df['Quantidade'].apply(lambda x: f"{x:.8f}")
        display_df['Custo/Valor Total (BRL)'] = display_df['Custo/Valor Total (BRL)'].apply(lambda x: f"R$ {x:,.2f}")

        # Formatar colunas que podem ser NaN (e que são numéricas)
        display_df['Preço Médio Compra na Op.'] = display_df['Preço Médio Compra na Op.'].apply(
            lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
        )
        display_df['Lucro/Prejuízo na Op.'] = display_df['Lucro/Prejuízo na Op.'].apply(
            lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
        )
        display_df['PTAX na Op.'] = display_df['PTAX na Op.'].apply(
            lambda x: f"{x:,.4f}" if pd.notna(x) else "-"
        )

        # Selecionar as colunas para exibir
        cols_to_display = ["Tipo", "Cripto", "Quantidade", "Custo/Valor Total (BRL)", "Preço Médio Compra na Op.", "Lucro/Prejuízo na Op.", "PTAX na Op.", "Data da Operação"]
        
        # Cria um contêiner para a tabela e o botão de exclusão
        for idx, row in display_df.iterrows():
            st.markdown("---") # Linha divisória para cada operação
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                for col_name in cols_to_display:
                    st.markdown(f"**{col_name}:** {row[col_name]}")
            with col2:
                if st.button("🗑️", key=f"delete_op_{row['id']}"):
                    st.session_state['confirm_delete_operation_id'] = row['id']
                    st.rerun()

        operation_confirm_placeholder = st.empty()
        if st.session_state.get('confirm_delete_operation_id'):
            with operation_confirm_placeholder.container():
                op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
                op_details = df_operacoes_historico[df_operacoes_historico['id'] == op_to_confirm_delete_id].iloc[0]

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
                    <p>Tem certeza que deseja excluir esta operação?</p>
                    <p>
                        **Tipo:** {op_details['tipo_operacao']} <br>
                        **Cripto:** {op_details['cripto']} <br>
                        **Quantidade:** {op_details['quantidade']:.8f} <br>
                        **Custo/Valor Total:** R$ {op_details['custo_total']:.2f} <br>
                        **Data:** {op_details['data_operacao'].strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
                with col_confirm_op:
                    if st.button("Sim, Excluir", key="confirm_op_delete_btn_modal"):
                        df_operacoes_updated = df_operacoes_historico[df_operacoes_historico['id'] != op_to_confirm_delete_id]
                        save_operacoes(df_operacoes_updated)
                        st.success("Operação excluída com sucesso!")
                        st.session_state['confirm_delete_operation_id'] = None
                        operation_confirm_placeholder.empty()
                        st.rerun()
                with col_cancel_op:
                    if st.button("Cancelar", key="cancel_op_delete_btn_modal"):
                        st.session_state['confirm_delete_operation_id'] = None
                        operation_confirm_placeholder.empty()
                        st.rerun()
        else:
            operation_confirm_placeholder.empty()

    else:
        st.info("Nenhuma operação registrada para esta carteira ainda.")


# --- Lógica Principal de Execução da Aplicação ---
# Inicialização do session_state de forma robusta
# Certifica-se de que st.session_state seja inicializado apenas uma vez
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "Portfólio"
if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = "login"

if 'accessed_wallet_id' not in st.session_state:
    st.session_state['accessed_wallet_id'] = None

if 'confirm_delete_wallet_id' not in st.session_state:
    st.session_state['confirm_delete_wallet_id'] = None
if 'confirm_delete_operation_id' not in st.session_state:
    st.session_state['confirm_delete_operation_id'] = None

# A lógica de autenticação e navegação
if st.session_state["logged_in"]:
    show_dashboard()
else:
    # --- Páginas de Autenticação ---
    if st.session_state["auth_page"] == "login":
        st.title("Bem-vindo ao Cripto Fácil! 🟧₿")
        st.subheader("Faça Login")
        with st.form("form_login"):
            login_cpf = st.text_input("CPF")
            login_password = st.text_input("Senha", type="password")
            login_button = st.form_submit_button("Entrar")
            if login_button:
                users_df = load_users()
                user_match = users_df[users_df['cpf'] == login_cpf]
                if not user_match.empty and user_match.iloc[0]['password_hash'] == hash_password(login_password):
                    st.session_state["logged_in"] = True
                    st.session_state["cpf"] = login_cpf
                    st.success("Login bem-sucedido!")
                    st.rerun()
                else:
                    st.error("CPF ou senha incorretos.")
        st.markdown("---")
        st.button("Criar Conta", on_click=lambda: st.session_state.update(auth_page="register"))
        st.button("Esqueci Minha Senha", on_click=lambda: st.session_state.update(auth_page="forgot_password"))

    elif st.session_state["auth_page"] == "register":
        st.title("Crie sua conta no Cripto Fácil 📝")
        with st.form("form_register"):
            reg_name = st.text_input("Nome Completo")
            reg_cpf = st.text_input("CPF")
            reg_phone = st.text_input("Telefone")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Senha", type="password")
            reg_confirm_password = st.text_input("Confirme a Senha", type="password")
            register_button = st.form_submit_button("Registrar")
            if register_button:
                users_df = load_users()
                if reg_cpf in users_df['cpf'].values:
                    st.error("CPF já cadastrado.")
                elif reg_password != reg_confirm_password:
                    st.error("As senhas não coincidem.")
                else:
                    new_user = pd.DataFrame([{
                        "cpf": reg_cpf,
                        "name": reg_name,
                        "phone": reg_phone,
                        "email": reg_email,
                        "password_hash": hash_password(reg_password)
                    }])
                    save_users(pd.concat([users_df, new_user], ignore_index=True))
                    st.success("Conta criada com sucesso! Faça login.")
                    st.session_state["auth_page"] = "login"
                    st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"))

    elif st.session_state["auth_page"] == "forgot_password":
        st.title("Recuperar Senha 🔑")
        with st.form("form_forgot_password"):
            forgot_cpf = st.text_input("Seu CPF")
            forgot_email = st.text_input("Seu Email Cadastrado")
            send_code_button = st.form_submit_button("Enviar Código de Recuperação")
            if send_code_button:
                users_df = load_users()
                user_match = users_df[(users_df['cpf'] == forgot_cpf) & (users_df['email'] == forgot_email)]
                if not user_match.empty:
                    send_recovery_code(forgot_email)
                    st.session_state["auth_page"] = "verify_code"
                    st.session_state["temp_cpf"] = forgot_cpf # Armazena o CPF temporariamente
                    st.rerun()
                else:
                    st.error("CPF ou Email não encontrados.")
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"))

    elif st.session_state["auth_page"] == "verify_code":
        st.title("Verificar Código e Redefinir Senha")
        st.write(f"Um código foi enviado para {st.session_state.get('reset_email', 'seu e-mail')}.")
        with st.form("form_verify_code"):
            input_code = st.text_input("Código de Recuperação")
            new_password = st.text_input("Nova Senha", type="password")
            confirm_new_password = st.text_input("Confirme a Nova Senha", type="password")
            verify_button = st.form_submit_button("Redefinir Senha")
            if verify_button:
                if input_code == st.session_state.get("recovery_code"):
                    if new_password == confirm_new_password:
                        users_df = load_users()
                        cpf_to_update = st.session_state.get("temp_cpf")
                        if cpf_to_update:
                            users_df.loc[users_df['cpf'] == cpf_to_update, 'password_hash'] = hash_password(new_password)
                            save_users(users_df)
                            st.success("Senha redefinida com sucesso! Faça login com sua nova senha.")
                            # Limpa os estados de recuperação
                            del st.session_state["recovery_code"]
                            del st.session_state["reset_email"]
                            del st.session_state["temp_cpf"]
                            st.session_state["auth_page"] = "login"
                            st.session_state["pagina_atual"] = "Portfólio" # Redireciona para o Portfólio após recuperação
                            st.rerun()
                        else:
                            st.error("Erro: CPF temporário não encontrado na sessão. Por favor, tente novamente a recuperação de senha.")
                    else:
                        st.error("As novas senhas não coincidem.")
                else:
                    st.error("Código de recuperação incorreto.")
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="forgot_password"))
