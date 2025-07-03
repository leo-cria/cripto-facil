import streamlit as st
import pandas as pd
import hashlib
import os
import random
import string
import uuid
from datetime import datetime
import time

# Configuração inicial da página Streamlit
st.set_page_config(page_title="Cripto Fácil", page_icon="🟧₿", layout="wide")

# Definição dos nomes dos arquivos para armazenar dados de usuários, carteiras e operações
USERS_FILE = "users.csv"
CARTEIRAS_FILE = "carteiras.csv"
OPERACOES_FILE = "operacoes.csv"

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

# --- Simulação de API de Criptomoedas ---
@st.cache_data
def fetch_cryptocurrencies_from_api():
    """
    Simula a chamada a uma API externa (e.g., CoinMarketCap) para obter uma lista de criptomoedas.
    """
    time.sleep(0.5)
    return ["BTC", "ETH", "SOL", "ADA", "XRP", "BNB", "DOGE", "SHIB", "DOT", "MATIC"]

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
                    <h4 style="color:#ff0000; margin-top:0;">⚠️ Confirmar Exclusão de Carteira</h4>
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

        cryptocurrencies = fetch_cryptocurrencies_from_api()
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
            # Removendo a prévia do valor em BRL para carteiras estrangeiras
            # valor_em_brl_preview = custo_total_input * ptax_input
            # st.info(f"Prévia do valor em BRL: R$ {valor_em_brl_preview:,.2f}")
            valor_em_brl_preview = custo_total_input * ptax_input # Calcular para salvar, mas não exibir
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

                # O custo_total que será salvo é sempre em BRL
                custo_total_final_brl = valor_em_brl_preview

                if current_op_type == "Compra":
                    if quantidade > 0:
                        preco_medio_compra_na_op = custo_total_final_brl / quantidade
                    else:
                        preco_medio_compra_na_op = float('nan') # Evita divisão por zero
                elif current_op_type == "Venda":
                    compras_anteriores = df_operacoes_existentes[
                        (df_operacoes_existentes['wallet_id'] == wallet_id) &
                        (df_operacoes_existentes['cpf_usuario'] == user_cpf) &
                        (df_operacoes_existentes['tipo_operacao'] == 'Compra') &
                        (df_operacoes_existentes['cripto'] == cripto) &
                        (df_operacoes_existentes['data_operacao'] <= data_hora_completa)
                    ]

                    if not compras_anteriores.empty and compras_anteriores['quantidade'].sum() > 0:
                        total_custo_compras = compras_anteriores['custo_total'].sum()
                        total_quantidade_compras = compras_anteriores['quantidade'].sum()

                        preco_medio_compra_na_op = total_custo_compras / total_quantidade_compras

                        custo_base_da_venda = quantidade * preco_medio_compra_na_op
                        lucro_prejuizo_na_op = custo_total_final_brl - custo_base_da_venda
                    else:
                        preco_medio_compra_na_op = float('nan')
                        lucro_prejuizo_na_op = float('nan')
                        st.warning("Não há operações de compra anteriores para calcular o preço médio para esta venda.")


                nova_operacao = pd.DataFrame([{
                    "id": f"operacao_{uuid.uuid4()}",
                    "wallet_id": wallet_id,
                    "cpf_usuario": user_cpf,
                    "tipo_operacao": current_op_type,
                    "cripto": cripto, # Corrigido: 'cripto' deve ser o símbolo (string)
                    "quantidade": float(quantidade), # Garante que a quantidade é salva como float
                    "custo_total": custo_total_final_brl, # Salva o valor já convertido para BRL
                    "data_operacao": data_hora_completa,
                    "preco_medio_compra_na_op": preco_medio_compra_na_op,
                    "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                    "ptax_na_op": ptax_input # Salva a PTAX utilizada
                }])

                save_operacoes(pd.concat([df_operacoes_existentes, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações Desta Carteira")

    op_confirm_placeholder = st.empty()
    if st.session_state.get('confirm_delete_operation_id'):
        with op_confirm_placeholder.container():
            op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
            df_operacoes = load_operacoes()

            if op_to_confirm_delete_id in df_operacoes['id'].values:
                op_details = df_operacoes[df_operacoes['id'] == op_to_confirm_delete_id].iloc[0]
                op_info_display = (f"{op_details['tipo_operacao']} de {op_details['quantidade']:.8f} "
                                f"{op_details['cripto']} (R$ {op_details['custo_total']:.2f}) em "
                                f"{op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}")

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-bottom:20px;">
                    <h4 style="color:#ff0000; margin-top:0;">⚠️ Confirmar Exclusão de Operação</h4>
                    <p>Tem certeza que deseja excluir a operação:<br> <strong>"{op_info_display}"</strong>?</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
                with col_confirm_op:
                    if st.button("Sim, Excluir", key="confirm_op_delete_btn_modal"):
                        df_ops_after_delete = df_operacoes[df_operacoes['id'] != op_to_confirm_delete_id]
                        save_operacoes(df_ops_after_delete)
                        st.success("Operação excluída com sucesso!")
                        st.session_state['confirm_delete_operation_id'] = None
                        op_confirm_placeholder.empty()
                        st.rerun()
                with col_cancel_op:
                    if st.button("Cancelar", key="cancel_op_delete_btn_modal"):
                        st.session_state['confirm_delete_operation_id'] = None
                        op_confirm_placeholder.empty()
                        st.rerun()
            else:
                st.session_state['confirm_delete_operation_id'] = None
                op_confirm_placeholder.empty()
                st.warning("A operação que você tentou excluir não foi encontrada.")
                st.rerun()
    else:
        op_confirm_placeholder.empty()

    df_operacoes = load_operacoes()
    wallet_operations_all = df_operacoes[
        (df_operacoes['wallet_id'] == wallet_id) &
        (df_operacoes['cpf_usuario'] == user_cpf)
    ].copy()

    wallet_origin_map = df_carteiras.set_index('id')['nacional'].to_dict()
    wallet_operations_all['origem_carteira'] = wallet_operations_all['wallet_id'].map(wallet_origin_map)

    # Adicionar coluna 'custo_total_usdt' para carteiras estrangeiras
    wallet_operations_all['custo_total_usdt'] = float('nan')
    if is_foreign_wallet:
        # Calcular o valor em USDT para cada operação se for carteira estrangeira
        # custo_total é em BRL, ptax_na_op é BRL/USDT
        wallet_operations_all['custo_total_usdt'] = wallet_operations_all.apply(
            lambda row: row['custo_total'] / row['ptax_na_op'] if pd.notna(row['ptax_na_op']) and row['ptax_na_op'] != 0 else float('nan'),
            axis=1
        )


    st.markdown("##### Filtros")
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        all_types = ['Compra', 'Venda']
        filter_type = st.multiselect("Tipo", all_types, key="filter_op_type")

    with col_filter2:
        all_cryptos_in_wallet = sorted(wallet_operations_all['cripto'].unique().tolist()) if not wallet_operations_all.empty else []
        filter_crypto = st.multiselect("Cripto", all_cryptos_in_wallet, key="filter_op_crypto")

    with col_filter3:
        filter_date_range = st.date_input("Data", value=[], key="filter_op_date_range")

    filtered_operations = wallet_operations_all.copy()

    if filter_type:
        filtered_operations = filtered_operations[filtered_operations['tipo_operacao'].isin(filter_type)]
    if filter_crypto:
        filtered_operations = filtered_operations[filtered_operations['cripto'].isin(filter_crypto)]
    if filter_date_range and len(filter_date_range) == 2:
        start_date, end_date = filter_date_range
        filtered_operations = filtered_operations[
            (filtered_operations['data_operacao'].dt.date >= start_date) &
            (filtered_operations['data_operacao'].dt.date <= end_date)
        ]
    elif filter_date_range and len(filter_date_range) == 1:
        single_date = filter_date_range[0]
        filtered_operations = filtered_operations[filtered_operations['data_operacao'].dt.date == single_date]

    if not filtered_operations.empty:
        # Definindo as colunas e seus respectivos ratios
        col_names = [
            "Tipo", "Cripto", "Qtd.", "PTAX",
            "Valor Total (USDT)", "Valor Total (BRL)", "P. Médio Compra",
            "P. Médio Venda", "Lucro/Prejuízo", "Data/Hora", "Origem", "Ações"
        ]
        # Ajustando os ratios das colunas para dar mais espaço à 'Ações'
        # Exemplo de ajuste: [0.06, 0.06, 0.09, 0.07, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.07, 0.08]
        # (Soma total deve ser 1.0 ou próximo)
        cols_ratio = [0.06, 0.07, 0.09, 0.07, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.07, 0.07] # Ajustei para 0.07 para 'Ações' e rebalanceei

        cols = st.columns(cols_ratio)
        for i, col_name in enumerate(col_names):
            with cols[i]:
                st.markdown(f"**{col_name}**")
        st.markdown("---")

        sorted_operations = filtered_operations.sort_values(by='data_operacao', ascending=False)

        for idx, op_row in sorted_operations.iterrows():
            cols = st.columns(cols_ratio)
            with cols[0]:
                st.write(op_row['tipo_operacao'])
            with cols[1]:
                st.write(op_row['cripto'])
            with cols[2]:
                st.write(f"{op_row['quantidade']:.8f}") # Garante 8 casas decimais na exibição
            with cols[3]: # PTAX
                if pd.notna(op_row['ptax_na_op']):
                    st.write(f"{op_row['ptax_na_op']:.4f}")
                else:
                    st.write("-")
            with cols[4]: # Valor Total (USDT)
                if is_foreign_wallet and pd.notna(op_row['custo_total_usdt']):
                    st.write(f'USDT {op_row["custo_total_usdt"]:.2f}')
                else:
                    st.write("-")
            with cols[5]: # Valor Total (BRL)
                st.write(f"R$ {op_row['custo_total']:.2f}") # Custo total já está em BRL
            with cols[6]:
                if op_row['tipo_operacao'] == 'Compra' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(f'R$ {op_row["preco_medio_compra_na_op']:.2f}')
                elif op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['preco_medio_compra_na_op']):
                    # Para vendas, o preço médio de compra na operação é o preço médio ponderado de aquisição
                    st.write(f'R$ {op_row["preco_medio_compra_na_op']:.2f}')
                else:
                    st.write("-")
            with cols[7]:
                if op_row['tipo_operacao'] == 'Venda' and op_row['quantidade'] > 0:
                    # Preço médio de venda é o custo_total da venda dividido pela quantidade
                    st.write(f'R$ {(op_row["custo_total"] / op_row["quantidade"]):.2f}')
                else:
                    st.write("-")
            with cols[8]:
                if op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['lucro_prejuizo_na_op']):
                    profit_loss = op_row['lucro_prejuizo_na_op']
                    color = "green" if profit_loss >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>R$ {profit_loss:.2f}</span>", unsafe_allow_html=True)
                else:
                    st.write("-")
            with cols[9]:
                st.write(op_row['data_operacao'].strftime('%d/%m/%Y %H:%M'))
            with cols[10]:
                st.write(op_row['origem_carteira'])
            with cols[11]: # Coluna Ações
                if st.button("🗑️", key=f"delete_op_{op_row['id']}", help="Excluir Operação"):
                    st.session_state['confirm_delete_operation_id'] = op_row['id']
                    st.rerun()

        st.markdown("---")
    else:
        st.info("Nenhuma operação registrada para esta carteira ou nenhum resultado para os filtros selecionados.")


# --- Funções para Exibição da Tela de Autenticação (Login, Cadastro, Recuperação) ---
def show_login():
    """
    Exibe as telas de autenticação: Login, Cadastro e Esqueceu a Senha.
    """
    df = load_users()

    st.markdown("""
    <h1 style='text-align:center;'>🟧₿ Cripto Fácil</h1>
    <p style='text-align:center;color:gray;'>Gestor de criptoativos com relatórios para IRPF</p><hr>
    """, unsafe_allow_html=True)

    # st.session_state inicializado no início do script, não aqui.

    if st.session_state["auth_page"] == "login":
        with st.form("login_form"):
            cpf = st.text_input("CPF")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
        if submitted:
            if df.empty:
                st.error("Nenhum usuário cadastrado.")
            elif df[(df["cpf"] == cpf) & (df["password_hash"] == hash_password(senha))].empty:
                st.error("CPF ou senha incorretos.")
            else:
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf
                st.session_state["pagina_atual"] = "Portfólio" # Define a página inicial após o login
                st.rerun()
        col1, col2 = st.columns(2)
        with col1:
            st.button("Cadastrar‑se", on_click=lambda: st.session_state.update(auth_page="register"), key="btn_cadastrar_login")
        with col2:
            st.button("Esqueci minha senha", on_click=lambda: st.session_state.update(auth_page="forgot"), key="btn_esqueci_senha_login")

    elif st.session_state["auth_page"] == "register":
        with st.form("register_form"):
            name = st.text_input("Nome completo")
            cpf = st.text_input("CPF")
            phone = st.text_input("Telefone")
            email = st.text_input("E‑mail")
            password = st.text_input("Senha", type="password")
            password_confirm = st.text_input("Confirme a senha", type="password")
            submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if password != password_confirm:
                st.error("Senhas não coincidem.")
            elif df[df["cpf"] == cpf].shape[0] > 0:
                st.error("CPF já cadastrado.")
            else:
                new_user = pd.DataFrame([{ "cpf": cpf, "name": name, "phone": phone, "email": email, "password_hash": hash_password(password)}])
                save_users(pd.concat([df, new_user], ignore_index=True))
                st.success("Cadastro realizado!")
                st.session_state["auth_page"] = "login"
                st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_cadastro")

    elif st.session_state["auth_page"] == "forgot":
        with st.form("forgot_form"):
            name = st.text_input("Nome Completo")
            cpf = st.text_input("CPF")
            email = st.text_input("E-mail")
            phone = st.text_input("Telefone")
            submitted = st.form_submit_button("Verificar e Acessar")
        if submitted:
            # Encontrar o usuário que corresponde a todas as informações
            matching_user = df[
                (df["name"] == name) &
                (df["cpf"] == cpf) &
                (df["email"] == email) &
                (df["phone"] == phone)
            ]
            if not matching_user.empty:
                st.success("Informações verificadas! Você pode agora acessar sua conta.")
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf # Usar o CPF encontrado para o login
                st.session_state["pagina_atual"] = "Portfólio" # Redireciona para o Portfólio após recuperação
                st.rerun()
            else:
                st.error("Dados informados não correspondem a nenhum usuário cadastrado.")
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_esqueci")

# --- Lógica Principal de Execução da Aplicação ---
# Inicialização do session_state de forma robusta
# Certifica-se de que st.session_state seja inicializado apenas uma vez
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = True # Alterado de False para True, conforme sua instrução
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "Portfólio"
if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = "login" # Garante que a página de auth padrão seja 'login'

if 'accessed_wallet_id' not in st.session_state:
    st.session_state['accessed_wallet_id'] = None

if 'confirm_delete_wallet_id' not in st.session_state:
    st.session_state['confirm_delete_wallet_id'] = None
if 'confirm_delete_operation_id' not in st.session_state:
    st.session_state['confirm_delete_operation_id'] = None

# A lógica de persistência de login é a maneira como você inicializa 'logged_in' e 'cpf'
# Se 'logged_in' já é True na sessão (o que acontece em uma atualização se não for resetado explicitamente),
# então o usuário permanece logado.
if st.session_state["logged_in"]:
    show_dashboard()
else:
    show_login()






não, teve esse erro: no codigo que me passu: File "/mount/src/cripto-facil/app.py", line 719 st.write(f'R$ {op_row["preco_medio_compra_na_op']:.2f}') ^SyntaxError: unterminated string literal (detected at line 719)




Mostrar raciocínio
Aqui está o código app.py corrigido. O erro SyntaxError: unterminated string literal na linha 719 foi causado por um conflito de aspas simples dentro de um f-string. Eu ajustei para usar aspas duplas para a chave do dicionário, o que é o padrão e evita o conflito.

A linha foi alterada de:
st.write(f'R$ {op_row["preco_medio_compra_na_op']:.2f}')
para:
st.write(f'R$ {op_row["preco_medio_compra_na_op"]:.2f}')

Python

import streamlit as st
import pandas as pd
import hashlib
import os
import random
import string
import uuid
from datetime import datetime
import time

# Configuração inicial da página Streamlit
st.set_page_config(page_title="Cripto Fácil", page_icon="🟧₿", layout="wide")

# Definição dos nomes dos arquivos para armazenar dados de usuários, carteiras e operações
USERS_FILE = "users.csv"
CARTEIRAS_FILE = "carteiras.csv"
OPERACOES_FILE = "operacoes.csv"

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

# --- Simulação de API de Criptomoedas ---
@st.cache_data
def fetch_cryptocurrencies_from_api():
    """
    Simula a chamada a uma API externa (e.g., CoinMarketCap) para obter uma lista de criptomoedas.
    """
    time.sleep(0.5)
    return ["BTC", "ETH", "SOL", "ADA", "XRP", "BNB", "DOGE", "SHIB", "DOT", "MATIC"]

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
                    <h4 style="color:#ff0000; margin-top:0;">⚠️ Confirmar Exclusão de Carteira</h4>
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

        cryptocurrencies = fetch_cryptocurrencies_from_api()
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
            # Removendo a prévia do valor em BRL para carteiras estrangeiras
            # valor_em_brl_preview = custo_total_input * ptax_input
            # st.info(f"Prévia do valor em BRL: R$ {valor_em_brl_preview:,.2f}")
            valor_em_brl_preview = custo_total_input * ptax_input # Calcular para salvar, mas não exibir
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

                # O custo_total que será salvo é sempre em BRL
                custo_total_final_brl = valor_em_brl_preview

                if current_op_type == "Compra":
                    if quantidade > 0:
                        preco_medio_compra_na_op = custo_total_final_brl / quantidade
                    else:
                        preco_medio_compra_na_op = float('nan') # Evita divisão por zero
                elif current_op_type == "Venda":
                    compras_anteriores = df_operacoes_existentes[
                        (df_operacoes_existentes['wallet_id'] == wallet_id) &
                        (df_operacoes_existentes['cpf_usuario'] == user_cpf) &
                        (df_operacoes_existentes['tipo_operacao'] == 'Compra') &
                        (df_operacoes_existentes['cripto'] == cripto) &
                        (df_operacoes_existentes['data_operacao'] <= data_hora_completa)
                    ]

                    if not compras_anteriores.empty and compras_anteriores['quantidade'].sum() > 0:
                        total_custo_compras = compras_anteriores['custo_total'].sum()
                        total_quantidade_compras = compras_anteriores['quantidade'].sum()

                        preco_medio_compra_na_op = total_custo_compras / total_quantidade_compras

                        custo_base_da_venda = quantidade * preco_medio_compra_na_op
                        lucro_prejuizo_na_op = custo_total_final_brl - custo_base_da_venda
                    else:
                        preco_medio_compra_na_op = float('nan')
                        lucro_prejuizo_na_op = float('nan')
                        st.warning("Não há operações de compra anteriores para calcular o preço médio para esta venda.")


                nova_operacao = pd.DataFrame([{
                    "id": f"operacao_{uuid.uuid4()}",
                    "wallet_id": wallet_id,
                    "cpf_usuario": user_cpf,
                    "tipo_operacao": current_op_type,
                    "cripto": cripto, # Corrigido: 'cripto' deve ser o símbolo (string)
                    "quantidade": float(quantidade), # Garante que a quantidade é salva como float
                    "custo_total": custo_total_final_brl, # Salva o valor já convertido para BRL
                    "data_operacao": data_hora_completa,
                    "preco_medio_compra_na_op": preco_medio_compra_na_op,
                    "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                    "ptax_na_op": ptax_input # Salva a PTAX utilizada
                }])

                save_operacoes(pd.concat([df_operacoes_existentes, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações Desta Carteira")

    op_confirm_placeholder = st.empty()
    if st.session_state.get('confirm_delete_operation_id'):
        with op_confirm_placeholder.container():
            op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
            df_operacoes = load_operacoes()

            if op_to_confirm_delete_id in df_operacoes['id'].values:
                op_details = df_operacoes[df_operacoes['id'] == op_to_confirm_delete_id].iloc[0]
                op_info_display = (f"{op_details['tipo_operacao']} de {op_details['quantidade']:.8f} "
                                f"{op_details['cripto']} (R$ {op_details['custo_total']:.2f}) em "
                                f"{op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}")

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-bottom:20px;">
                    <h4 style="color:#ff0000; margin-top:0;">⚠️ Confirmar Exclusão de Operação</h4>
                    <p>Tem certeza que deseja excluir a operação:<br> <strong>"{op_info_display}"</strong>?</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
                with col_confirm_op:
                    if st.button("Sim, Excluir", key="confirm_op_delete_btn_modal"):
                        df_ops_after_delete = df_operacoes[df_operacoes['id'] != op_to_confirm_delete_id]
                        save_operacoes(df_ops_after_delete)
                        st.success("Operação excluída com sucesso!")
                        st.session_state['confirm_delete_operation_id'] = None
                        op_confirm_placeholder.empty()
                        st.rerun()
                with col_cancel_op:
                    if st.button("Cancelar", key="cancel_op_delete_btn_modal"):
                        st.session_state['confirm_delete_operation_id'] = None
                        op_confirm_placeholder.empty()
                        st.rerun()
            else:
                st.session_state['confirm_delete_operation_id'] = None
                op_confirm_placeholder.empty()
                st.warning("A operação que você tentou excluir não foi encontrada.")
                st.rerun()
    else:
        op_confirm_placeholder.empty()

    df_operacoes = load_operacoes()
    wallet_operations_all = df_operacoes[
        (df_operacoes['wallet_id'] == wallet_id) &
        (df_operacoes['cpf_usuario'] == user_cpf)
    ].copy()

    wallet_origin_map = df_carteiras.set_index('id')['nacional'].to_dict()
    wallet_operations_all['origem_carteira'] = wallet_operations_all['wallet_id'].map(wallet_origin_map)

    # Adicionar coluna 'custo_total_usdt' para carteiras estrangeiras
    wallet_operations_all['custo_total_usdt'] = float('nan')
    if is_foreign_wallet:
        # Calcular o valor em USDT para cada operação se for carteira estrangeira
        # custo_total é em BRL, ptax_na_op é BRL/USDT
        wallet_operations_all['custo_total_usdt'] = wallet_operations_all.apply(
            lambda row: row['custo_total'] / row['ptax_na_op'] if pd.notna(row['ptax_na_op']) and row['ptax_na_op'] != 0 else float('nan'),
            axis=1
        )


    st.markdown("##### Filtros")
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        all_types = ['Compra', 'Venda']
        filter_type = st.multiselect("Tipo", all_types, key="filter_op_type")

    with col_filter2:
        all_cryptos_in_wallet = sorted(wallet_operations_all['cripto'].unique().tolist()) if not wallet_operations_all.empty else []
        filter_crypto = st.multiselect("Cripto", all_cryptos_in_wallet, key="filter_op_crypto")

    with col_filter3:
        filter_date_range = st.date_input("Data", value=[], key="filter_op_date_range")

    filtered_operations = wallet_operations_all.copy()

    if filter_type:
        filtered_operations = filtered_operations[filtered_operations['tipo_operacao'].isin(filter_type)]
    if filter_crypto:
        filtered_operations = filtered_operations[filtered_operations['cripto'].isin(filter_crypto)]
    if filter_date_range and len(filter_date_range) == 2:
        start_date, end_date = filter_date_range
        filtered_operations = filtered_operations[
            (filtered_operations['data_operacao'].dt.date >= start_date) &
            (filtered_operations['data_operacao'].dt.date <= end_date)
        ]
    elif filter_date_range and len(filter_date_range) == 1:
        single_date = filter_date_range[0]
        filtered_operations = filtered_operations[filtered_operations['data_operacao'].dt.date == single_date]

    if not filtered_operations.empty:
        # Definindo as colunas e seus respectivos ratios
        col_names = [
            "Tipo", "Cripto", "Qtd.", "PTAX",
            "Valor Total (USDT)", "Valor Total (BRL)", "P. Médio Compra",
            "P. Médio Venda", "Lucro/Prejuízo", "Data/Hora", "Origem", "Ações"
        ]
        # Ajustando os ratios das colunas para dar mais espaço à 'Ações'
        # Exemplo de ajuste: [0.06, 0.06, 0.09, 0.07, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.07, 0.08]
        # (Soma total deve ser 1.0 ou próximo)
        cols_ratio = [0.06, 0.07, 0.09, 0.07, 0.11, 0.11, 0.11, 0.11, 0.11, 0.11, 0.07, 0.07] # Ajustei para 0.07 para 'Ações' e rebalanceei

        cols = st.columns(cols_ratio)
        for i, col_name in enumerate(col_names):
            with cols[i]:
                st.markdown(f"**{col_name}**")
        st.markdown("---")

        sorted_operations = filtered_operations.sort_values(by='data_operacao', ascending=False)

        for idx, op_row in sorted_operations.iterrows():
            cols = st.columns(cols_ratio)
            with cols[0]:
                st.write(op_row['tipo_operacao'])
            with cols[1]:
                st.write(op_row['cripto'])
            with cols[2]:
                st.write(f"{op_row['quantidade']:.8f}") # Garante 8 casas decimais na exibição
            with cols[3]: # PTAX
                if pd.notna(op_row['ptax_na_op']):
                    st.write(f"{op_row['ptax_na_op']:.4f}")
                else:
                    st.write("-")
            with cols[4]: # Valor Total (USDT)
                if is_foreign_wallet and pd.notna(op_row['custo_total_usdt']):
                    st.write(f'USDT {op_row["custo_total_usdt"]:.2f}')
                else:
                    st.write("-")
            with cols[5]: # Valor Total (BRL)
                st.write(f"R$ {op_row['custo_total']:.2f}") # Custo total já está em BRL
            with cols[6]:
                if op_row['tipo_operacao'] == 'Compra' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(f'R$ {op_row["preco_medio_compra_na_op"]:.2f}') # LINHA CORRIGIDA AQUI
                elif op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['preco_medio_compra_na_op']):
                    # Para vendas, o preço médio de compra na operação é o preço médio ponderado de aquisição
                    st.write(f'R$ {op_row["preco_medio_compra_na_op"]:.2f}')
                else:
                    st.write("-")
            with cols[7]:
                if op_row['tipo_operacao'] == 'Venda' and op_row['quantidade'] > 0:
                    # Preço médio de venda é o custo_total da venda dividido pela quantidade
                    st.write(f'R$ {(op_row["custo_total"] / op_row["quantidade"]):.2f}')
                else:
                    st.write("-")
            with cols[8]:
                if op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['lucro_prejuizo_na_op']):
                    profit_loss = op_row['lucro_prejuizo_na_op']
                    color = "green" if profit_loss >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>R$ {profit_loss:.2f}</span>", unsafe_allow_html=True)
                else:
                    st.write("-")
            with cols[9]:
                st.write(op_row['data_operacao'].strftime('%d/%m/%Y %H:%M'))
            with cols[10]:
                st.write(op_row['origem_carteira'])
            with cols[11]: # Coluna Ações
                if st.button("🗑️", key=f"delete_op_{op_row['id']}", help="Excluir Operação"):
                    st.session_state['confirm_delete_operation_id'] = op_row['id']
                    st.rerun()

        st.markdown("---")
    else:
        st.info("Nenhuma operação registrada para esta carteira ou nenhum resultado para os filtros selecionados.")


# --- Funções para Exibição da Tela de Autenticação (Login, Cadastro, Recuperação) ---
def show_login():
    """
    Exibe as telas de autenticação: Login, Cadastro e Esqueceu a Senha.
    """
    df = load_users()

    st.markdown("""
    <h1 style='text-align:center;'>🟧₿ Cripto Fácil</h1>
    <p style='text-align:center;color:gray;'>Gestor de criptoativos com relatórios para IRPF</p><hr>
    """, unsafe_allow_html=True)

    # st.session_state inicializado no início do script, não aqui.

    if st.session_state["auth_page"] == "login":
        with st.form("login_form"):
            cpf = st.text_input("CPF")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
        if submitted:
            if df.empty:
                st.error("Nenhum usuário cadastrado.")
            elif df[(df["cpf"] == cpf) & (df["password_hash"] == hash_password(senha))].empty:
                st.error("CPF ou senha incorretos.")
            else:
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf
                st.session_state["pagina_atual"] = "Portfólio" # Define a página inicial após o login
                st.rerun()
        col1, col2 = st.columns(2)
        with col1:
            st.button("Cadastrar‑se", on_click=lambda: st.session_state.update(auth_page="register"), key="btn_cadastrar_login")
        with col2:
            st.button("Esqueci minha senha", on_click=lambda: st.session_state.update(auth_page="forgot"), key="btn_esqueci_senha_login")

    elif st.session_state["auth_page"] == "register":
        with st.form("register_form"):
            name = st.text_input("Nome completo")
            cpf = st.text_input("CPF")
            phone = st.text_input("Telefone")
            email = st.text_input("E‑mail")
            password = st.text_input("Senha", type="password")
            password_confirm = st.text_input("Confirme a senha", type="password")
            submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if password != password_confirm:
                st.error("Senhas não coincidem.")
            elif df[df["cpf"] == cpf].shape[0] > 0:
                st.error("CPF já cadastrado.")
            else:
                new_user = pd.DataFrame([{ "cpf": cpf, "name": name, "phone": phone, "email": email, "password_hash": hash_password(password)}])
                save_users(pd.concat([df, new_user], ignore_index=True))
                st.success("Cadastro realizado!")
                st.session_state["auth_page"] = "login"
                st.rerun()
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_cadastro")

    elif st.session_state["auth_page"] == "forgot":
        with st.form("forgot_form"):
            name = st.text_input("Nome Completo")
            cpf = st.text_input("CPF")
            email = st.text_input("E-mail")
            phone = st.text_input("Telefone")
            submitted = st.form_submit_button("Verificar e Acessar")
        if submitted:
            # Encontrar o usuário que corresponde a todas as informações
            matching_user = df[
                (df["name"] == name) &
                (df["cpf"] == cpf) &
                (df["email"] == email) &
                (df["phone"] == phone)
            ]
            if not matching_user.empty:
                st.success("Informações verificadas! Você pode agora acessar sua conta.")
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf # Usar o CPF encontrado para o login
                st.session_state["pagina_atual"] = "Portfólio" # Redireciona para o Portfólio após recuperação
                st.rerun()
            else:
                st.error("Dados informados não correspondem a nenhum usuário cadastrado.")
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_esqueci")

# --- Lógica Principal de Execução da Aplicação ---
# Inicialização do session_state de forma robusta
# Certifica-se de que st.session_state seja inicializado apenas uma vez
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = True # Alterado de False para True, conforme sua instrução
if "pagina_atual" not in st.session_state:
    st.session_state["pagina_atual"] = "Portfólio"
if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = "login" # Garante que a página de auth padrão seja 'login'

if 'accessed_wallet_id' not in st.session_state:
    st.session_state['accessed_wallet_id'] = None

if 'confirm_delete_wallet_id' not in st.session_state:
    st.session_state['confirm_delete_wallet_id'] = None
if 'confirm_delete_operation_id' not in st.session_state:
    st.session_state['confirm_delete_operation_id'] = None

# A lógica de persistência de login é a maneira como você inicializa 'logged_in' e 'cpf'
# Se 'logged_in' já é True na sessão (o que acontece em uma atualização se não for resetado explicitamente),
# então o usuário permanece logado.
if st.session_state["logged_in"]:
    show_dashboard()
else:
    show_login()
