import streamlit as st
import pandas as pd
import hashlib
import os
import random
import string
import uuid
from datetime import datetime, date
import time
import json
import re # Importar regex para validação do input manual

# Configuração inicial da página Streamlit
st.set_page_config(page_title="Cripto Fácil", page_icon="🟧₿", layout="wide")

# Definição dos nomes dos arquivos para armazenar dados de usuários, carteiras e operações
USERS_FILE = "users.csv"
CARTEIRAS_FILE = "carteiras.csv"
OPERACOES_FILE = "operacoes.csv"
CRYPTOS_FILE = "cryptos.json" # Novo arquivo para criptomoedas

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
        
        # Garante que a coluna 'cripto' seja do tipo string e substitui 'nan' literal
        if 'cripto' in df.columns:
            df['cripto'] = df['cripto'].astype(str).replace('nan', '') 
        
        # --- NOVO: Garante que a coluna 'cripto_display_name' exista ---
        if 'cripto_display_name' not in df.columns:
            # Para dados antigos, tenta construir um display_name a partir do símbolo
            df['cripto_display_name'] = df['cripto'].apply(
                lambda x: f"{x} - (Nome Desconhecido)" if pd.notna(x) and str(x).strip() != '' else ""
            )
        else:
            df['cripto_display_name'] = df['cripto_display_name'].astype(str).replace('nan', '')

        # --- NOVO: Garante que a coluna 'cripto_image_url' exista ---
        if 'cripto_image_url' not in df.columns:
            # Para dados antigos, usa o emoji de moeda como padrão
            df['cripto_image_url'] = "🪙"
        else:
            df['cripto_image_url'] = df['cripto_image_url'].astype(str).replace('nan', '🪙')


        return df
    return pd.DataFrame(columns=[
        "id", "wallet_id", "cpf_usuario", "tipo_operacao", "cripto",
        "quantidade", "custo_total", "data_operacao",
        "preco_medio_compra_na_op",
        "lucro_prejuizo_na_op",
        "ptax_na_op",
        "cripto_display_name", # Adicionada nova coluna
        "cripto_image_url" # Adicionada nova coluna
    ])

def save_operacoes(df):
    """Salva o DataFrame de operações no arquivo CSV."""
    df['data_operacao'] = df['data_operacao'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df.to_csv(OPERACOES_FILE, index=False)

# --- Função para carregar criptomoedas de um arquivo local ---
@st.cache_data
def load_cryptocurrencies_from_file():
    """
    Carrega a lista de criptomoedas de um arquivo JSON local.
    Retorna uma lista vazia se o arquivo não existir ou houver erro.
    O formato esperado é um dicionário com 'last_updated_timestamp' e 'cryptos',
    onde 'cryptos' é uma lista de dicionários com 'symbol', 'name', 'image', 'display_name' e 'current_price_brl'.
    """
    if os.path.exists(CRYPTOS_FILE):
        try:
            with open(CRYPTOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # A nova estrutura tem "last_updated_timestamp" e "cryptos"
                last_updated = data.get("last_updated_timestamp")
                cryptos = data.get("cryptos", [])
                
                # Converte a lista de dicionários para um DataFrame para fácil manipulação
                # Certifica-se de que 'current_price_brl' é float
                df_cryptos = pd.DataFrame(cryptos)
                if 'current_price_brl' in df_cryptos.columns:
                    # CORREÇÃO: Preenche NaN com 0.0 para garantir que o preço seja numérico
                    df_cryptos['current_price_brl'] = pd.to_numeric(df_cryptos['current_price_brl'], errors='coerce').fillna(0.0)
                
                return last_updated, df_cryptos
        except json.JSONDecodeError:
            st.error(f"Erro ao decodificar o arquivo {CRYPTOS_FILE}. Verifique o formato JSON.")
            return None, pd.DataFrame(columns=["symbol", "name", "image", "display_name", "current_price_brl"])
    else:
        st.warning(f"Arquivo '{CRYPTOS_FILE}' não encontrado. Execute 'gerar_cryptos_json.py' para criá-lo.")
        return None, pd.DataFrame(columns=["symbol", "name", "image", "display_name", "current_price_brl"])

def get_current_crypto_price(crypto_symbol, df_cryptos_prices):
    """
    Retorna o preço atual de uma criptomoeda em BRL do DataFrame de preços.
    """
    price_row = df_cryptos_prices[df_cryptos_prices['symbol'] == crypto_symbol]
    if not price_row.empty:
        # Pega o primeiro preço encontrado para o símbolo, já garantido como numérico (float ou 0.0)
        return price_row['current_price_brl'].iloc[0]
    return 0.0 # Retorna 0.0 se não encontrar o preço

# Função para formatar valores monetários para o padrão brasileiro
def format_currency_brl(value):
    """Formata um valor numérico para o padrão monetário brasileiro (R$ X.XXX,XX)."""
    # Garante que o valor é um número antes de formatar
    if pd.isna(value):
        return "-"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Nova função para formatar números com vírgula para decimais e ponto para milhares
def format_number_br(value, decimals=2):
    """
    Formata um valor numérico para o padrão brasileiro (ponto para milhares, vírgula para decimais).
    Args:
        value: O valor numérico a ser formatado.
        decimals: Número de casas decimais.
    Returns:
        Uma string com o valor formatado.
    """
    if pd.isna(value):
        return "-"
    # Convertendo para string com o número de casas decimais desejado
    formatted_value = f"{value:,.{decimals}f}"
    # Substituindo a vírgula por 'X' temporariamente para evitar conflito
    formatted_value = formatted_value.replace(",", "X")
    # Substituindo o ponto por vírgula para o separador decimal
    formatted_value = formatted_value.replace(".", ",")
    # Substituindo 'X' de volta por ponto para o separador de milhares
    formatted_value = formatted_value.replace("X", ".")
    return formatted_value


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

        for page_name in ["Portfólio", "Minha Conta", "Carteiras", "Relatórios", "Imposto de Renda"]:
            if st.button(page_name, key=f"sidebar_btn_{page_name.lower().replace(' ', '_')}"):
                st.session_state["pagina_atual"] = page_name
                st.session_state["accessed_wallet_id"] = None
                st.session_state["confirm_delete_wallet_id"] = None
                st.session_state["confirm_delete_operation_id"] = None
                st.session_state['confirm_delete_account_step1'] = False # Reset confirmation step for account deletion
                st.rerun()

        st.markdown("---")
        if st.button("🔒 Sair"):
            st.session_state["logged_in"] = False
            st.session_state["auth_page"] = "login"
            st.session_state["pagina_atual"] = "Portfólio"
            st.session_state["accessed_wallet_id"] = None
            st.session_state["confirm_delete_wallet_id"] = None
            st.session_state["confirm_delete_operation_id"] = None
            st.session_state['confirm_delete_account_step1'] = False # Reset confirmation step for account deletion
            st.rerun()

    page = st.session_state.get("pagina_atual", "Portfólio")
    # Título da página dinâmico
    st.title(pages[page])

    # Carrega os dados mais recentes das criptomoedas e a data de atualização
    last_updated_timestamp, df_cryptos_prices = load_cryptocurrencies_from_file()
    
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

        # NEW ADDITION: Excluir Conta section
        with st.expander("Excluir conta"):
            # Initialize session state for the two-step confirmation if not already present
            if 'confirm_delete_account_step1' not in st.session_state:
                st.session_state['confirm_delete_account_step1'] = False
            
            if not st.session_state['confirm_delete_account_step1']:
                with st.form("form_delete_account_password"):
                    st.warning("⚠️ **Atenção:** A exclusão da conta é permanente e removerá todos os seus dados, carteiras e operações associadas.")
                    delete_password = st.text_input("Confirme sua senha atual para excluir", type="password", key="delete_account_password_input")
                    submit_delete_request = st.form_submit_button("Solicitar Exclusão da Conta")

                    if submit_delete_request:
                        if hash_password(delete_password) != usuario['password_hash']:
                            st.error("Senha incorreta. Não foi possível prosseguir com a exclusão.")
                        else:
                            st.session_state['confirm_delete_account_step1'] = True
                            st.rerun() # Rerun to show the confirmation prompt
            else: # Step 2: Show confirmation
                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Conta</h4>
                    <p>Tem certeza que deseja excluir <strong>PERMANENTEMENTE</strong> sua conta?</p>
                    <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível e excluirá TODOS os seus dados, carteiras e operações associadas!</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_confirm_delete, col_cancel_delete = st.columns([0.3, 0.7])
                with col_confirm_delete:
                    if st.button("Sim, Excluir Permanentemente", key="confirm_permanent_delete_btn"):
                        # Perform deletion
                        df_users = load_users()
                        df_carteiras = load_carteiras()
                        df_operacoes = load_operacoes()

                        # Filter out current user's data
                        df_users_updated = df_users[df_users['cpf'] != st.session_state["cpf"]]
                        df_carteiras_updated = df_carteiras[df_carteiras['cpf_usuario'] != st.session_state["cpf"]]
                        df_operacoes_updated = df_operacoes[df_operacoes['cpf_usuario'] != st.session_state["cpf"]]

                        save_users(df_users_updated)
                        save_carteiras(df_carteiras_updated)
                        save_operacoes(df_operacoes_updated)

                        st.success("Sua conta e todos os dados associados foram excluídos com sucesso.")
                        
                        # Log out user and reset all relevant session states
                        st.session_state["logged_in"] = False
                        st.session_state["auth_page"] = "login"
                        st.session_state["pagina_atual"] = "Portfólio"
                        st.session_state["accessed_wallet_id"] = None
                        st.session_state["confirm_delete_wallet_id"] = None
                        st.session_state["confirm_delete_operation_id"] = None
                        st.session_state['confirm_delete_account_step1'] = False # Reset step
                        st.rerun() # Redirect to login
                with col_cancel_delete:
                    if st.button("Cancelar", key="cancel_permanent_delete_btn"):
                        st.session_state['confirm_delete_account_step1'] = False # Reset step
                        st.rerun() # Rerun to hide the confirmation box

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
                            st.session_state['confirm_delete_account_step1'] = False # Reset confirmation step for account deletion
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
    
    # Carrega os dados de criptomoedas para ter os preços atuais
    last_updated_timestamp, cryptocurrencies_data_df = load_cryptocurrencies_from_file()
    crypto_prices = {crypto['symbol'].upper(): crypto.get('current_price_brl', 0.0) for crypto in cryptocurrencies_data_df.to_dict('records')}

    # Título do Portfólio Consolidado com a data de atualização
    col_portfolio_title, col_update_date_placeholder = st.columns([0.7, 0.3]) # Placeholder para alinhar
    with col_portfolio_title:
        st.markdown("#### Portfólio Consolidado da Carteira")
    # A data de atualização será exibida junto com o Valor Atual da Carteira para alinhamento

    df_operacoes_portfolio = load_operacoes()
    wallet_ops_for_portfolio = df_operacoes_portfolio[
        (df_operacoes_portfolio['wallet_id'] == wallet_id) &
        (df_operacoes_portfolio['cpf_usuario'] == user_cpf)
    ].copy()

    total_lucro_realizado = 0.0
    total_valor_atual_carteira = 0.0

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
        # Agrupa por símbolo da cripto para calcular o portfólio atual
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

                # Obter o preço atual da criptomoeda
                current_price = crypto_prices.get(cripto_simbolo.upper(), 0.0) # Garante que é float
                valor_atual_posicao = quantidade_atual * current_price
                total_valor_atual_carteira += valor_atual_posicao # Adiciona ao total da carteira

                # --- NOVO: Pega o display_name e image_url da última operação registrada para essa cripto ---
                # Isso garante que o nome e imagem exibidos no portfólio correspondam ao que foi salvo na operação
                last_op_for_crypto = ops_cripto.sort_values(by='data_operacao', ascending=False).iloc[0]
                display_name_for_portfolio = last_op_for_crypto['cripto_display_name']
                image_url_for_portfolio = last_op_for_crypto['cripto_image_url']
                portfolio_detail[cripto_simbolo] = {
                    'display_name': display_name_for_portfolio, # Usa o display_name da operação
                    'image': image_url_for_portfolio, # Usa a image_url da operação
                    'quantidade': float(quantidade_atual),
                    'custo_total': float(custo_total_atual_estimado),
                    'custo_medio': float(custo_medio),
                    'lucro_realizado': float(lucro_realizado_cripto),
                    'current_price_brl': float(current_price),
                    'valor_atual_posicao': float(valor_atual_posicao)
                }
        
        # Criar DataFrame para o portfólio detalhado
        portfolio_df = pd.DataFrame.from_dict(portfolio_detail, orient='index')
        if not portfolio_df.empty:
            # --- CORREÇÃO: Renomear colunas explicitamente para evitar KeyError e garantir casing ---
            portfolio_df = portfolio_df.reset_index().rename(columns={
                'index': 'Cripto_Symbol', # O símbolo original da cripto (do índice)
                'display_name': 'Cripto', # O display_name da cripto
                'image': 'Logo', # A URL da imagem ou emoji (RENOMEADO)
                'quantidade': 'Quantidade', # A quantidade atual
                'custo_total': 'Custo Total', # O custo total
                'custo_medio': 'Custo Médio', # O custo médio
                'lucro_realizado': 'Lucro Realizado', # O lucro realizado
                'current_price_brl': 'Preço Atual (BRL)', # O preço atual em BRL
                'valor_atual_posicao': 'Valor Atual da Posição' # O valor atual da posição
            })
            portfolio_df = portfolio_df[portfolio_df['Quantidade'] > 0] # Filtrar só as que tem saldo > 0

            # Calcular o Custo Total da Carteira com base no portfolio_df filtrado
            total_custo_carteira_atualizado = portfolio_df['Custo Total'].sum()
        else:
            total_custo_carteira_atualizado = 0.0

        # Exibir as métricas em texto
        col_custo, col_lucro, col_valor_atual = st.columns(3)
        with col_custo:
            st.markdown(
                f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Custo Total da Carteira (Ativo) (BRL)</p>" # Adicionado (BRL)
                f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_custo_carteira_atualizado)}</p>",
                unsafe_allow_html=True
            )
        with col_lucro:
            # Aplicar cor ao Lucro Realizado Total da Carteira
            color_lucro_total = "green" if total_lucro_realizado > 0 else ("red" if total_lucro_realizado < 0 else "black")
            st.markdown(
                f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Lucro Realizado Total da Carteira (BRL)</p>" # Adicionado (BRL)
                f"<p style='text-align: center; color: {color_lucro_total}; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_lucro_realizado)}</p>",
                unsafe_allow_html=True
            )
        with col_valor_atual:
            st.markdown(
                f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Valor Atual da Carteira (BRL)</p>" # Adicionado (BRL)
                f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_valor_atual_carteira)}</p>",
                unsafe_allow_html=True
            )
        # --- NOVO: Alinhamento da data de atualização ---
        if last_updated_timestamp:
            try:
                updated_dt = datetime.fromisoformat(last_updated_timestamp)
                st.markdown(f"<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Atualizado em: {updated_dt.strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)
            except ValueError:
                st.markdown("<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Data de atualização não disponível.</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Data de atualização não disponível.</p>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Portfolio Atual Detalhado")

        if not portfolio_df.empty:
            # Calcular a coluna POSIÇÃO
            if total_valor_atual_carteira > 0:
                portfolio_df['POSIÇÃO'] = (portfolio_df['Valor Atual da Posição'] / total_valor_atual_carteira) * 100
            else:
                portfolio_df['POSIÇÃO'] = 0.0

            # --- NOVO: Ordenar por 'POSIÇÃO' em ordem decrescente ---
            portfolio_df = portfolio_df.sort_values(by='POSIÇÃO', ascending=False)

            # Definindo as colunas e seus respectivos ratios (REMOVIDAS: Custo Médio e Preço Atual (BRL))
            col_names_portfolio = ["Logo", "Cripto", "Quantidade", "Custo Total (BRL)", "Lucro Realizado (BRL)", "Valor Atual da Posição (BRL)", "POSIÇÃO"] # RENOMEADO E ADICIONADO (BRL)
            cols_ratio_portfolio = [0.07, 0.15, 0.15, 0.15, 0.15, 0.18, 0.15] # Ajustado para 7 colunas

            cols_portfolio = st.columns(cols_ratio_portfolio)
            for i, col_name in enumerate(col_names_portfolio):
                with cols_portfolio[i]:
                    st.markdown(f"**{col_name}**")
            st.markdown("---") # Linha divisória para cabeçalho

            for idx, row in portfolio_df.iterrows():
                cols_portfolio_data = st.columns(cols_ratio_portfolio)
                with cols_portfolio_data[0]: # Logo
                    st.image(row['Logo'], width=24) if "http" in row['Logo'] else st.markdown(f"**{row['Logo']}**")
                with cols_portfolio_data[1]: # Cripto Display Name
                    st.write(row['Cripto'])
                with cols_portfolio_data[2]: # Quantidade
                    st.write(format_number_br(row['Quantidade'], decimals=8))
                with cols_portfolio_data[3]: # Custo Total
                    st.write(format_currency_brl(row['Custo Total']))
                with cols_portfolio_data[4]: # Lucro Realizado
                    color_lucro = "green" if row['Lucro Realizado'] > 0 else ("red" if row['Lucro Realizado'] < 0 else "black")
                    st.markdown(f"<span style='color:{color_lucro};'>{format_currency_brl(row['Lucro Realizado'])}</span>", unsafe_allow_html=True)
                with cols_portfolio_data[5]: # Valor Atual da Posição
                    st.write(format_currency_brl(row['Valor Atual da Posição']))
                with cols_portfolio_data[6]: # Posição %
                    st.write(f"{format_number_br(row['POSIÇÃO'], decimals=2)}%")

        else:
            st.info("Nenhum ativo no portfólio desta carteira ainda.")

    st.markdown("---")
    st.markdown("#### Registrar Nova Operação")

    # Define as opções para tipo de operação
    tipo_operacao = st.radio("Tipo de Operação", ["Compra", "Venda"], horizontal=True, key="tipo_operacao_radio")

    # Carrega as criptomoedas e cria uma lista formatada para o seletor
    _, all_cryptos_df = load_cryptocurrencies_from_file()
    
    # Filtra criptos que têm um símbolo válido e um display_name
    valid_cryptos = all_cryptos_df[
        (all_cryptos_df['symbol'].notna()) & 
        (all_cryptos_df['display_name'].notna()) &
        (all_cryptos_df['symbol'] != '') & 
        (all_cryptos_df['display_name'] != '')
    ].copy()

    # Adiciona a imagem no início do display_name para o selectbox
    valid_cryptos['display_name_with_image'] = valid_cryptos.apply(
        lambda row: f"{row['image']} {row['display_name']} ({row['symbol'].upper()})", axis=1
    )
    # Garante que o símbolo é maiúsculo para uso posterior
    valid_cryptos['symbol_upper'] = valid_cryptos['symbol'].str.upper()

    # Cria um mapeamento de display_name_with_image para symbol_upper
    crypto_display_to_symbol_map = dict(zip(valid_cryptos['display_name_with_image'], valid_cryptos['symbol_upper']))
    # Cria uma lista de opções para o selectbox
    crypto_options_for_selectbox = valid_cryptos['display_name_with_image'].tolist()

    # Adiciona uma opção vazia no início
    crypto_options_for_selectbox.insert(0, "Selecione a Criptomoeda")
    
    with st.form("form_add_operacao"):
        
        selected_crypto_display = st.selectbox(
            "Criptomoeda",
            options=crypto_options_for_selectbox,
            key="cripto_select_box"
        )
        
        # Obtém o símbolo da cripto selecionada usando o mapeamento
        cripto_simbolo_selecionada = crypto_display_to_symbol_map.get(selected_crypto_display, "")
        
        # Pega as informações da cripto selecionada do DataFrame 'all_cryptos_df'
        # Isso garante que 'cripto_display_name' e 'cripto_image_url' sejam precisos
        selected_crypto_info = all_cryptos_df[all_cryptos_df['symbol'].str.upper() == cripto_simbolo_selecionada].iloc[0] if cripto_simbolo_selecionada else None
        
        cripto_display_name = selected_crypto_info['display_name'] if selected_crypto_info is not None else ""
        cripto_image_url = selected_crypto_info['image'] if selected_crypto_info is not None else "🪙" # Padrão para emoji de moeda
        
        current_price_brl = get_current_crypto_price(cripto_simbolo_selecionada, all_cryptos_df) if cripto_simbolo_selecionada else 0.0

        if cripto_simbolo_selecionada and current_price_brl > 0:
            st.info(f"Preço atual de **{cripto_display_name}** ({cripto_simbolo_selecionada.upper()}): {format_currency_brl(current_price_brl)}")
        elif cripto_simbolo_selecionada:
            st.warning(f"Preço atual de {cripto_display_name} ({cripto_simbolo_selecionada.upper()}) não disponível ou 0.")

        col1, col2 = st.columns(2)
        with col1:
            quantidade = st.number_input("Quantidade", min_value=0.00000001, format="%.8f", key="quantidade_input")
        with col2:
            custo_total = st.number_input(
                "Custo/Receita Total (BRL)",
                min_value=0.0,
                format="%.2f",
                help="Custo total em BRL para compra, ou receita total em BRL para venda.",
                key="custo_total_input"
            )
            # Input para PTax se for carteira estrangeira
            ptax_na_op = 0.0
            if is_foreign_wallet:
                ptax_na_op = st.number_input(
                    "PTax na data da operação (para carteiras estrangeiras)",
                    min_value=0.0,
                    format="%.4f",
                    help="Taxa de câmbio PTax Venda no fechamento do dia da operação.",
                    key="ptax_input"
                )
        
        data_operacao = st.date_input("Data da Operação", value="today", key="data_operacao_input")
        hora_operacao = st.time_input("Hora da Operação", value=datetime.now().time(), key="hora_operacao_input")

        # Combine data e hora
        datahora_operacao = datetime.combine(data_operacao, hora_operacao)

        submitted_op = st.form_submit_button("Registrar Operação 💾")

        if submitted_op:
            if not cripto_simbolo_selecionada or selected_crypto_display == "Selecione a Criptomoeda":
                st.error("Por favor, selecione uma criptomoeda.")
            elif quantidade <= 0 or custo_total <= 0:
                st.error("Quantidade e Custo/Receita Total devem ser maiores que zero.")
            elif is_foreign_wallet and ptax_na_op <= 0:
                 st.error("Para carteiras estrangeiras, o valor do PTax na data da operação é obrigatório e deve ser maior que zero.")
            else:
                df_operacoes = load_operacoes()
                
                # Calcular preço médio de compra na operação (para fins de custo de aquisição em venda)
                preco_medio_compra_na_op = 0.0
                if tipo_operacao == 'Compra':
                    preco_medio_compra_na_op = custo_total / quantidade if quantidade > 0 else 0.0
                else: # Venda
                    # Para vendas, precisamos do custo médio ponderado atual para calcular o lucro/prejuízo
                    # e registrar o preço médio de compra que esta venda está "liquidando"
                    
                    # Carrega todas as operações do usuário para a cripto específica
                    historico_compras_cripto = df_operacoes[
                        (df_operacoes['cpf_usuario'] == user_cpf) &
                        (df_operacoes['wallet_id'] == wallet_id) &
                        (df_operacoes['cripto'].str.upper() == cripto_simbolo_selecionada.upper()) &
                        (df_operacoes['tipo_operacao'] == 'Compra')
                    ].copy()

                    if not historico_compras_cripto.empty:
                        # Certifica que 'custo_total' e 'quantidade' são numéricos
                        historico_compras_cripto['custo_total'] = pd.to_numeric(historico_compras_cripto['custo_total'], errors='coerce')
                        historico_compras_cripto['quantidade'] = pd.to_numeric(historico_compras_cripto['quantidade'], errors='coerce')

                        total_comprado_em_qtd = historico_compras_cripto['quantidade'].sum()
                        total_comprado_em_custo = historico_compras_cripto['custo_total'].sum()
                        
                        # Incluir as vendas prévias para calcular a quantidade e custo remanescente
                        historico_vendas_cripto = df_operacoes[
                            (df_operacoes['cpf_usuario'] == user_cpf) &
                            (df_operacoes['wallet_id'] == wallet_id) &
                            (df_operacoes['cripto'].str.upper() == cripto_simbolo_selecionada.upper()) &
                            (df_operacoes['tipo_operacao'] == 'Venda')
                        ].copy()

                        if not historico_vendas_cripto.empty:
                            historico_vendas_cripto['quantidade'] = pd.to_numeric(historico_vendas_cripto['quantidade'], errors='coerce')
                            # Subtrai a quantidade vendida anteriormente da quantidade comprada
                            total_comprado_em_qtd -= historico_vendas_cripto['quantidade'].sum()
                            # Subtrai o custo base das vendas anteriores do custo total comprado
                            total_comprado_em_custo -= (historico_vendas_cripto['quantidade'] * historico_vendas_cripto['preco_medio_compra_na_op']).sum()

                        if total_comprado_em_qtd > 0:
                            preco_medio_compra_na_op = total_comprado_em_custo / total_comprado_em_qtd
                        else:
                            preco_medio_compra_na_op = 0.0 # Sem compras suficientes ou saldo para cobrir a venda
                    else:
                        preco_medio_compra_na_op = 0.0 # Nenhuma compra registrada para esta cripto

                lucro_prejuizo = 0.0
                if tipo_operacao == 'Venda':
                    # Lucro/Prejuízo = Receita da Venda - (Quantidade Vendida * Preço Médio de Compra)
                    lucro_prejuizo = custo_total - (quantidade * preco_medio_compra_na_op)
                
                nova_operacao = pd.DataFrame([{
                    "id": f"operacao_{uuid.uuid4()}",
                    "wallet_id": wallet_id,
                    "cpf_usuario": user_cpf,
                    "tipo_operacao": tipo_operacao,
                    "cripto": cripto_simbolo_selecionada.upper(),
                    "quantidade": float(quantidade),
                    "custo_total": float(custo_total),
                    "data_operacao": datahora_operacao,
                    "preco_medio_compra_na_op": float(preco_medio_compra_na_op),
                    "lucro_prejuizo_na_op": float(lucro_prejuizo),
                    "ptax_na_op": float(ptax_na_op),
                    "cripto_display_name": cripto_display_name,
                    "cripto_image_url": cripto_image_url
                }])
                save_operacoes(pd.concat([df_operacoes, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações")

    df_operacoes_historico = load_operacoes()
    wallet_operations = df_operacoes_historico[
        (df_operacoes_historico['wallet_id'] == wallet_id) &
        (df_operacoes_historico['cpf_usuario'] == user_cpf)
    ].sort_values(by='data_operacao', ascending=False)

    if not wallet_operations.empty:
        # Preparar dados para exibição
        display_df = wallet_operations.copy()
        
        # Usar 'cripto_display_name' para a coluna 'Cripto' e 'cripto_image_url' para 'Logo'
        display_df['Cripto'] = display_df.apply(
            lambda row: f"{row['cripto_image_url']} {row['cripto_display_name']}" if "http" not in row['cripto_image_url'] else f"<img src='{row['cripto_image_url']}' style='vertical-align:middle; width:24px; height:24px;'> {row['cripto_display_name']}",
            axis=1
        )
        display_df['Data/Hora'] = display_df['data_operacao'].dt.strftime('%d/%m/%Y %H:%M')
        display_df['Quantidade'] = display_df['quantidade'].apply(lambda x: format_number_br(x, decimals=8))
        display_df['Custo/Receita Total'] = display_df['custo_total'].apply(format_currency_brl)
        display_df['Preço Médio Compra na OP'] = display_df['preco_medio_compra_na_op'].apply(format_currency_brl)
        
        display_df['Lucro/Prejuízo na OP'] = display_df['lucro_prejuizo_na_op'].apply(format_currency_brl)
        display_df['PTax na OP'] = display_df['ptax_na_op'].apply(lambda x: format_number_br(x, decimals=4) if x > 0 else "-")
        
        # Adiciona cor ao texto de Lucro/Prejuízo
        display_df['Lucro/Prejuízo na OP Formatado'] = display_df.apply(
            lambda row: f"<span style='color: {'green' if row['lucro_prejuizo_na_op'] > 0 else ('red' if row['lucro_prejuizo_na_op'] < 0 else 'black')};'>{row['Lucro/Prejuízo na OP']}</span>",
            axis=1
        )
        
        # Filtra as colunas para exibição
        columns_to_display = [
            'Cripto', 'Tipo de Operação', 'Quantidade', 'Custo/Receita Total',
            'Preço Médio Compra na OP', 'Lucro/Prejuízo na OP Formatado', 'PTax na OP', 'Data/Hora', 'id'
        ]
        
        # Renomeia colunas para exibição amigável
        display_df_final = display_df[columns_to_display].rename(columns={
            'tipo_operacao': 'Tipo de Operação',
            'Lucro/Prejuízo na OP Formatado': 'Lucro/Prejuízo na OP'
        })

        # Exibir tabela
        st.write("Clique na linha para mais detalhes ou para excluir a operação:")
        
        # Adiciona uma coluna para o botão de exclusão
        display_df_final['Ação'] = [f"🗑️ Excluir_{op_id}" for op_id in display_df_final['id']]

        # Configura as colunas para a tabela interativa
        column_config = {
            "Cripto": st.column_config.Column(
                "Cripto",
                help="Criptomoeda da operação",
                width="small"
            ),
            "Tipo de Operação": st.column_config.TextColumn(
                "Tipo de Operação",
                help="Tipo da operação (Compra/Venda)",
                width="small"
            ),
            "Quantidade": st.column_config.TextColumn(
                "Quantidade",
                help="Quantidade de criptomoeda",
                width="small"
            ),
            "Custo/Receita Total": st.column_config.TextColumn(
                "Custo/Receita Total",
                help="Custo ou receita total da operação em BRL",
                width="small"
            ),
            "Preço Médio Compra na OP": st.column_config.TextColumn(
                "Preço Médio Compra na OP",
                help="Preço médio de compra apurado na data da operação (para vendas, é o custo de aquisição da unidade vendida)",
                width="small"
            ),
            "Lucro/Prejuízo na OP": st.column_config.TextColumn(
                "Lucro/Prejuízo na OP",
                help="Lucro ou prejuízo realizado com esta operação (apenas para vendas)",
                width="small"
            ),
            "PTax na OP": st.column_config.TextColumn(
                "PTax na OP",
                help="Taxa PTax Venda utilizada na operação (para carteiras estrangeiras)",
                width="small"
            ),
            "Data/Hora": st.column_config.DatetimeColumn(
                "Data/Hora",
                help="Data e hora da operação",
                format="DD/MM/YYYY HH:mm",
                width="medium"
            ),
            "id": None, # Esconde a coluna ID
            "Ação": st.column_config.ButtonColumn(
                "Ação",
                help="Clique para excluir a operação",
                width="small",
                key="delete_op_button",
                on_click=lambda op_id: st.session_state.update(confirm_delete_operation_id=op_id),
                args=display_df_final['id']
            )
        }
        
        st.data_editor(
            display_df_final,
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            key="operations_data_editor"
        )
        
        # Confirmation for operation deletion
        if st.session_state.get('confirm_delete_operation_id'):
            op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
            op_details = wallet_operations[wallet_operations['id'] == op_to_confirm_delete_id].iloc[0]

            st.markdown(f"""
            <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
                <p>Tem certeza que deseja excluir a operação de <strong>{op_details['tipo_operacao']}</strong> de <strong>{op_details['quantidade']} {op_details['cripto']}</strong>?</p>
                <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível!</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
            with col_confirm_op:
                if st.button("Sim, Excluir Operação", key="confirm_op_delete_btn"):
                    df_operacoes_current = load_operacoes()
                    df_operacoes_updated = df_operacoes_current[df_operacoes_current['id'] != op_to_confirm_delete_id]
                    save_operacoes(df_operacoes_updated)
                    st.success("Operação excluída com sucesso!")
                    st.session_state['confirm_delete_operation_id'] = None
                    st.rerun()
            with col_cancel_op:
                if st.button("Cancelar", key="cancel_op_delete_btn"):
                    st.session_state['confirm_delete_operation_id'] = None
                    st.rerun()

    else:
        st.info("Nenhuma operação registrada para esta carteira ainda.")

# --- Lógica de Autenticação e Navegação de Páginas ---
def login_page():
    st.title("Cripto Fácil - Login")
    st.subheader("Acesse sua conta")
    with st.form("login_form"):
        cpf = st.text_input("CPF (somente números)", max_chars=11)
        password = st.text_input("Senha", type="password")
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("Entrar")
        with col2:
            st.button("Esqueci a Senha", on_click=lambda: st.session_state.update(auth_page="forgot_password"))

        if login_button:
            df = load_users()
            user_found = df[df['cpf'] == cpf]
            if not user_found.empty and user_found.iloc[0]['password_hash'] == hash_password(password):
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf
                st.session_state["pagina_atual"] = "Portfólio"
                st.session_state["auth_page"] = "dashboard" # Redireciona para o dashboard
                st.rerun()
            else:
                st.error("CPF ou senha inválidos.")

def register_page():
    st.title("Cripto Fácil - Cadastro")
    st.subheader("Crie sua conta")
    with st.form("register_form"):
        cpf = st.text_input("CPF (somente números)", max_chars=11, help="Será seu login de acesso.")
        name = st.text_input("Nome Completo")
        phone = st.text_input("Telefone (com DDD)", max_chars=15)
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password", help="Mínimo 6 caracteres.")
        confirm_password = st.text_input("Confirme a Senha", type="password")

        register_button = st.form_submit_button("Cadastrar")

        if register_button:
            df = load_users()
            if not cpf.strip() or not name.strip() or not phone.strip() or not email.strip() or not password.strip() or not confirm_password.strip():
                st.error("Todos os campos são obrigatórios.")
            elif not re.fullmatch(r'\d{11}', cpf):
                st.error("CPF deve conter exatamente 11 dígitos numéricos.")
            elif len(password) < 6:
                st.error("A senha deve ter no mínimo 6 caracteres.")
            elif password != confirm_password:
                st.error("As senhas não coincidem.")
            elif cpf in df['cpf'].values:
                st.error("CPF já cadastrado.")
            elif email in df['email'].values:
                st.error("Email já cadastrado.")
            else:
                new_user = pd.DataFrame([{
                    "cpf": cpf,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "password_hash": hash_password(password)
                }])
                save_users(pd.concat([df, new_user], ignore_index=True))
                st.success("Cadastro realizado com sucesso! Você já pode fazer login.")
                st.session_state["auth_page"] = "login"
                st.rerun()
    st.button("Voltar para Login", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_cadastro")

def forgot_password_page():
    st.title("Cripto Fácil - Recuperar Senha")
    st.subheader("Informe seu e-mail para receber o código de recuperação")
    if "recovery_step" not in st.session_state:
        st.session_state["recovery_step"] = "request_code" # request_code, verify_code, reset_password

    if st.session_state["recovery_step"] == "request_code":
        with st.form("form_request_code"):
            email_rec = st.text_input("Email cadastrado", key="email_recovery_input")
            submit_email = st.form_submit_button("Solicitar Código de Recuperação")
            if submit_email:
                df = load_users()
                user_found = df[df['email'] == email_rec]
                if not user_found.empty:
                    send_recovery_code(email_rec)
                    st.session_state["recovery_step"] = "verify_code"
                    st.session_state["reset_cpf"] = user_found.iloc[0]['cpf'] # Armazena o CPF para uso posterior
                    st.rerun()
                else:
                    st.error("E-mail não encontrado.")
    
    elif st.session_state["recovery_step"] == "verify_code":
        st.info(f"Código enviado para: {st.session_state.get('reset_email', 'seu email')}")
        with st.form("form_verify_code"):
            code_input = st.text_input("Código de Recuperação", key="code_input")
            submit_code = st.form_submit_button("Verificar Código")
            if submit_code:
                if code_input == st.session_state.get("recovery_code"):
                    st.success("Código verificado com sucesso!")
                    st.session_state["recovery_step"] = "reset_password"
                    st.rerun()
                else:
                    st.error("Código incorreto.")
        st.button("Reenviar Código", on_click=lambda: st.session_state.update(recovery_step="request_code"), key="btn_reenviar_codigo")


    elif st.session_state["recovery_step"] == "reset_password":
        with st.form("form_reset_password"):
            new_pass = st.text_input("Nova Senha", type="password", key="new_password_input")
            confirm_new_pass = st.text_input("Confirme a Nova Senha", type="password", key="confirm_new_password_input")
            submit_reset = st.form_submit_button("Redefinir Senha")
            if submit_reset:
                if len(new_pass) < 6:
                    st.error("A nova senha deve ter no mínimo 6 caracteres.")
                elif new_pass != confirm_new_pass:
                    st.error("As senhas não coincidem.")
                else:
                    df = load_users()
                    cpf_to_reset = st.session_state.get("reset_cpf")
                    if cpf_to_reset:
                        df.loc[df['cpf'] == cpf_to_reset, 'password_hash'] = hash_password(new_pass)
                        save_users(df)
                        st.success("Senha redefinida com sucesso! Faça login com sua nova senha.")
                        # Limpa estados de recuperação
                        del st.session_state["recovery_code"]
                        del st.session_state["reset_email"]
                        del st.session_state["recovery_step"]
                        del st.session_state["reset_cpf"]
                        st.session_state["auth_page"] = "login"
                        st.rerun()
                    else:
                        st.error("Erro: CPF não encontrado para o login")
        st.button("Voltar", on_click=lambda: st.session_state.update(auth_page="login"), key="btn_voltar_esqueci")

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
if 'confirm_delete_account_step1' not in st.session_state: # NEW: for account deletion confirmation
    st.session_state['confirm_delete_account_step1'] = False


if st.session_state["logged_in"]:
    show_dashboard()
else:
    if st.session_state["auth_page"] == "login":
        login_page()
        st.markdown("---")
        st.markdown("Não tem conta? [Cadastre-se](javascript:void(0));", unsafe_allow_html=True)
        if st.button("Cadastrar", key="go_to_register_btn"):
            st.session_state["auth_page"] = "register"
            st.rerun()
    elif st.session_state["auth_page"] == "register":
        register_page()
    elif st.session_state["auth_page"] == "forgot_password":
        forgot_password_page()
        
