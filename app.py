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
                st.session_state["confirm_delete_account"] = False # Resetar estado de exclusão de conta
                st.session_state["edit_operation_id"] = None # Resetar estado de edição de operação
                st.rerun()

        st.markdown("---")
        if st.button("🔒 Sair"):
            st.session_state["logged_in"] = False
            st.session_state["auth_page"] = "login"
            st.session_state["pagina_atual"] = "Portfólio"
            st.session_state["accessed_wallet_id"] = None
            st.session_state["confirm_delete_wallet_id"] = None
            st.session_state["confirm_delete_operation_id"] = None
            st.session_state["confirm_delete_account"] = False # Resetar estado de exclusão de conta
            st.session_state["edit_operation_id"] = None # Resetar estado de edição de operação
            st.rerun()

    page = st.session_state.get("pagina_atual", "Portfólio")
    # Título da página dinâmico
    st.title(pages[page])

    # Carrega os dados mais recentes das criptomoedas e a data de atualização
    last_updated_timestamp, df_cryptos_prices = load_cryptocurrencies_from_file()
    
    if page == "Minha Conta":
        df_users = load_users()
        usuario = df_users[df_users['cpf'] == st.session_state["cpf"]].iloc[0]

        st.subheader("Meus Dados Cadastrais")

        # --- Alterar Dados Cadastrais (Retrátil com Confirmação de Senha) ---
        with st.expander("Alterar Dados Cadastrais ⚙️"):
            with st.form("form_account"):
                st.text_input("Nome", value=usuario['name'], disabled=True) # Nome permanece disabled
                st.text_input("CPF", value=usuario['cpf'], disabled=True)   # CPF permanece disabled
                
                # Campos editáveis
                new_phone = st.text_input("Telefone", value=usuario['phone'])
                new_email = st.text_input("Email", value=usuario['email'])
                
                # Senha para confirmar alterações
                confirm_password_cad = st.text_input("Digite sua senha atual para confirmar", type="password", key="confirm_password_cad")
                
                submitted = st.form_submit_button("Salvar alterações ✅")
                if submitted:
                    if hash_password(confirm_password_cad) == usuario['password_hash']:
                        df_users.loc[df_users['cpf'] == usuario['cpf'], ['phone', 'email']] = new_phone, new_email
                        save_users(df_users)
                        st.success("Dados atualizados com sucesso!")
                        st.rerun() # Recarrega a página para mostrar os dados atualizados
                    else:
                        st.error("Senha atual incorreta. As alterações não foram salvas.")

        # --- Alterar Senha ---
        with st.expander("Alterar senha 🔑"):
            with st.form("form_password"):
                atual = st.text_input("Senha atual", type="password")
                nova = st.text_input("Nova senha", type="password")
                confirmar = st.text_input("Confirme a nova senha", type="password")
                ok = st.form_submit_button("Alterar senha")
                if ok:
                    if hash_password(atual) != usuario['password_hash']:
                        st.error("Senha atual incorreta.")
                    elif nova != confirmar:
                        st.error("Nova senha não confere.")
                    else:
                        df_users.loc[df_users['cpf'] == usuario['cpf'], 'password_hash'] = hash_password(nova)
                        save_users(df_users)
                        st.success("Senha alterada com sucesso!")
                        st.rerun() # Recarrega a página para limpar os campos da senha

        # --- Excluir Conta (Retrátil com Confirmação de Senha e Modal) ---
        with st.expander("Excluir Conta ⚠️"):
            with st.form("form_delete_account"):
                st.warning("Esta ação é irreversível e excluirá todos os seus dados, carteiras e operações.")
                delete_password = st.text_input("Digite sua senha para confirmar a exclusão", type="password", key="delete_password_confirm")
                delete_button_clicked = st.form_submit_button("Excluir minha conta permanentemente")

                if delete_button_clicked:
                    if hash_password(delete_password) == usuario['password_hash']:
                        st.session_state['confirm_delete_account'] = True
                        st.session_state['delete_account_password_verified'] = True # Sinaliza que a senha foi verificada
                    else:
                        st.error("Senha incorreta. Não é possível prosseguir com a exclusão.")
                        st.session_state['confirm_delete_account'] = False # Reseta a confirmação

            # Modal de confirmação (fora do formulário para permitir rerun)
            if st.session_state.get('confirm_delete_account') and st.session_state.get('delete_account_password_verified'):
                st.markdown("""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;">🛑 CONFIRMAR EXCLUSÃO DA CONTA</h4>
                    <p style="font-weight:bold;">Você está prestes a excluir sua conta permanentemente.</p>
                    <p style="color:#ff0000; font-weight:bold;">Todos os seus dados (informações de usuário, carteiras e todas as operações) serão APAGADOS e não poderão ser recuperados.</p>
                    <p>Tem certeza absoluta que deseja continuar?</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_del, col_cancel_del = st.columns([0.2, 0.8])
                with col_confirm_del:
                    if st.button("SIM, EXCLUIR TUDO", key="final_confirm_delete_account"):
                        # Excluir carteiras e operações do usuário
                        df_carteiras = load_carteiras()
                        df_carteiras_updated = df_carteiras[df_carteiras['cpf_usuario'] != st.session_state["cpf"]]
                        save_carteiras(df_carteiras_updated)

                        df_operacoes = load_operacoes()
                        df_operacoes_updated = df_operacoes[df_operacoes['cpf_usuario'] != st.session_state["cpf"]]
                        save_operacoes(df_operacoes_updated)
                        
                        # Excluir o usuário
                        df_users_updated = df_users[df_users['cpf'] != st.session_state["cpf"]]
                        save_users(df_users_updated)

                        st.success("Sua conta e todos os dados associados foram excluídos com sucesso.")
                        # Deslogar e redirecionar para a tela de login
                        st.session_state["logged_in"] = False
                        st.session_state["auth_page"] = "login"
                        st.session_state["pagina_atual"] = "Portfólio"
                        st.session_state["accessed_wallet_id"] = None
                        st.session_state["confirm_delete_wallet_id"] = None
                        st.session_state["confirm_delete_operation_id"] = None
                        st.session_state["confirm_delete_account"] = False # Resetar
                        st.session_state['delete_account_password_verified'] = False # Resetar
                        st.rerun()
                with col_cancel_del:
                    if st.button("Cancelar", key="cancel_final_delete_account"):
                        st.session_state['confirm_delete_account'] = False
                        st.session_state['delete_account_password_verified'] = False # Resetar
                        st.info("Exclusão da conta cancelada.")
                        st.rerun() # Limpa o modal de confirmação

    elif page == "Carteiras":
        df_carteiras = load_carteiras()
        user_cpf = st.session_state["cpf"]
        user_carteiras_df = df_carteiras[df_carteiras['cpf_usuario'] == user_cpf].copy()

        # --- Formulário de cadastro de carteira dentro de um expander ---
        with st.expander("Cadastrar Carteira ➕", expanded=False): # Alterado o título e o estado inicial para fechado
            st.subheader("Cadastrar nova carteira") # Removido a caixa
            
            tipo_selecionado_criar = st.radio(
                "Tipo de carteira",
                ["Auto Custódia", "Corretora", "Banco"], # Adicionado o tipo Banco
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
                elif tipo_selecionado_criar == "Corretora":
                    nome_input_criar = st.selectbox("Corretora", ["BINANCE", "BYBIT", "COINBASE", "OKX", "MEXC", "MERCADO BITCOIN"], key="corretora_selector_criar")
                elif tipo_selecionado_criar == "Banco": # Novo tipo Banco
                    nome_input_criar = st.selectbox("Instituição Financeira", ["NUBANK", "ITAU", "MERCADO PAGO", "BRADESCO"], key="banco_selector_criar")
                    pass

                nacional_input_criar = st.radio("Origem da carteira:", ["Nacional", "Estrangeira"], key="nacionalidade_radio_field_criar")

                enviado_criar = st.form_submit_button("Cadastrar carteira ➕") # Alterado o texto do botão
                if enviado_criar:
                    if tipo_selecionado_criar == "Auto Custódia" and (not nome_input_criar or not info1_input_criar):
                        st.error("Por favor, preencha todos os campos obrigatórios para Auto Custódia.")
                    elif (tipo_selecionado_criar == "Corretora" or tipo_selecionado_criar == "Banco") and not nome_input_criar:
                        st.error("Por favor, selecione uma corretora ou instituição financeira.")
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
                            st.session_state["confirm_delete_account"] = False # Resetar estado de exclusão de conta
                            st.session_state["edit_operation_id"] = None # Resetar estado de edição de operação
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
                wallet_name = user_carteiras_df[user_carteiras_df['id'] == wallet_to_confirm_delete_id]['nome'].iloc[0]

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Carteira</h4>
                    <p>Você tem certeza que deseja excluir a carteira <strong>"{wallet_name}"</strong>?</p>
                    <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível e também excluirá TODAS as operações vinculadas a esta carteira!</p>
                    <p>Deseja realmente continuar?</p>
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
    st.subheader("Registrar Nova Operação")

    last_updated_timestamp, df_cryptos_prices = load_cryptocurrencies_from_file()
    
    # Prepara a lista de opções para o selectbox da criptomoeda
    crypto_options = ["Pesquisar manualmente (símbolo)"] + sorted(df_cryptos_prices['display_name'].tolist())

    with st.form("form_add_operacao"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_operacao = st.selectbox(
                "Tipo de Operação",
                ["Compra", "Venda", "Deposito Fiat", "Saque Fiat", "Transferência Recebida", "Transferência Enviada"],
                key="tipo_operacao_select"
            )
        with col2:
            data_operacao = st.date_input("Data da Operação", value=datetime.now().date(), key="data_operacao_input")
            
        # Campos para criptomoeda (condicional)
        if tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"]:
            
            crypto_selection_method = st.radio(
                "Como você deseja selecionar a criptomoeda?",
                ["Selecionar da lista", "Pesquisar manualmente (símbolo)"],
                key="crypto_selection_method_radio",
                horizontal=True
            )

            selected_crypto_symbol = None
            selected_crypto_name = None
            selected_crypto_image = None
            
            if crypto_selection_method == "Selecionar da lista":
                selected_crypto_display_name = st.selectbox(
                    "Criptomoeda", 
                    crypto_options, 
                    key="crypto_dropdown",
                    help="Selecione a criptomoeda da lista ou pesquise manualmente pelo símbolo."
                )
                
                if selected_crypto_display_name and selected_crypto_display_name != "Pesquisar manualmente (símbolo)":
                    crypto_row = df_cryptos_prices[df_cryptos_prices['display_name'] == selected_crypto_display_name].iloc[0]
                    selected_crypto_symbol = crypto_row['symbol']
                    selected_crypto_name = crypto_row['name']
                    selected_crypto_image = crypto_row['image']
                
            if crypto_selection_method == "Pesquisar manualmente (símbolo)" or selected_crypto_display_name == "Pesquisar manualmente (símbolo)":
                manual_crypto_symbol = st.text_input("Símbolo da Criptomoeda (Ex: BTC, ETH)", key="manual_crypto_symbol_input").upper()
                if manual_crypto_symbol:
                    # Tenta encontrar a criptomoeda na lista carregada
                    crypto_row = df_cryptos_prices[df_cryptos_prices['symbol'] == manual_crypto_symbol]
                    if not crypto_row.empty:
                        selected_crypto_symbol = crypto_row.iloc[0]['symbol']
                        selected_crypto_name = crypto_row.iloc[0]['name']
                        selected_crypto_image = crypto_row.iloc[0]['image']
                        st.success(f"Criptomoeda encontrada: {selected_crypto_name} ({selected_crypto_symbol})")
                    else:
                        st.warning(f"Símbolo '{manual_crypto_symbol}' não encontrado na lista. Será registrado como está.")
                        selected_crypto_symbol = manual_crypto_symbol
                        selected_crypto_name = f"Nome desconhecido para {manual_crypto_symbol}" # Nome padrão
                        selected_crypto_image = "❓" # Imagem padrão

            if not selected_crypto_symbol: # Se nenhuma cripto foi selecionada por qualquer método
                st.warning("Por favor, selecione ou insira o símbolo da criptomoeda.")
                
            quantidade = st.number_input("Quantidade da Criptomoeda", min_value=0.00000001, format="%.8f", key="quantidade_input")

        # Custo total (apenas para Compra e Venda)
        custo_total = 0.0
        if tipo_operacao in ["Compra", "Venda"]:
            custo_total = st.number_input("Custo Total (em BRL ou moeda base da carteira)", min_value=0.0, format="%.8f", key="custo_total_input")
        
        # PTAX para carteiras estrangeiras
        ptax_na_op = 0.0
        if is_foreign_wallet and tipo_operacao in ["Compra", "Venda"]:
            st.info("Para carteiras estrangeiras, por favor, insira a PTAX (taxa de câmbio) do dia da operação.")
            ptax_na_op = st.number_input("PTAX (para carteiras estrangeiras)", min_value=0.00000001, format="%.4f", key="ptax_na_op_input")

        submitted = st.form_submit_button("Registrar Operação ✅")

        if submitted:
            if tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"] and not selected_crypto_symbol:
                st.error("Por favor, selecione ou insira o símbolo da criptomoeda para esta operação.")
            elif quantidade <= 0 and tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"]:
                st.error("A quantidade da criptomoeda deve ser maior que zero.")
            elif custo_total <= 0 and tipo_operacao in ["Compra", "Venda"]:
                st.error("O custo total deve ser maior que zero para operações de compra/venda.")
            elif is_foreign_wallet and tipo_operacao in ["Compra", "Venda"] and ptax_na_op <= 0:
                st.error("Para carteiras estrangeiras, a PTAX deve ser maior que zero para operações de compra/venda.")
            else:
                preco_medio_compra_na_op = 0.0
                if tipo_operacao in ["Compra", "Venda"] and quantidade > 0:
                    preco_medio_compra_na_op = custo_total / quantidade
                
                lucro_prejuizo_na_op = 0.0 # Calculado posteriormente ou para venda

                nova_operacao = pd.DataFrame([{
                    "id": f"operacao_{uuid.uuid4()}", # ID único para a operação
                    "wallet_id": wallet_id,
                    "cpf_usuario": user_cpf,
                    "tipo_operacao": tipo_operacao,
                    "cripto": selected_crypto_symbol, # Salva o símbolo
                    "cripto_display_name": selected_crypto_name, # Salva o nome de exibição
                    "cripto_image_url": selected_crypto_image, # Salva a URL da imagem
                    "quantidade": quantidade,
                    "custo_total": custo_total,
                    "data_operacao": data_operacao.strftime('%Y-%m-%d %H:%M:%S'), # Formato para salvar
                    "preco_medio_compra_na_op": preco_medio_compra_na_op,
                    "lucro_prejuizo_na_op": lucro_prejuizo_na_op, # Por enquanto 0, será atualizado em vendas
                    "ptax_na_op": ptax_na_op
                }])
                current_operacoes_df = load_operacoes()
                save_operacoes(pd.concat([current_operacoes_df, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                st.rerun()

    st.markdown("---")
    st.subheader("Histórico de Operações")
    df_operacoes = load_operacoes()
    wallet_operacoes_df = df_operacoes[
        (df_operacoes['cpf_usuario'] == user_cpf) &
        (df_operacoes['wallet_id'] == wallet_id)
    ].sort_values(by='data_operacao', ascending=False).copy()

    # Filtro de operações
    if not wallet_operacoes_df.empty:
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_tipo = st.multiselect(
                "Filtrar por Tipo de Operação",
                options=wallet_operacoes_df['tipo_operacao'].unique(),
                default=[]
            )
        with col_filter2:
            filter_crypto = st.multiselect(
                "Filtrar por Criptomoeda",
                options=wallet_operacoes_df['cripto'].unique(),
                default=[]
            )
        with col_filter3:
            # Novo: Campo de pesquisa de texto livre para Criptomoeda
            search_crypto_text = st.text_input("Pesquisar Criptomoeda (símbolo ou nome)", "").lower()


        filtered_operacoes_df = wallet_operacoes_df.copy()

        if filter_tipo:
            filtered_operacoes_df = filtered_operacoes_df[filtered_operacoes_df['tipo_operacao'].isin(filter_tipo)]
        if filter_crypto:
            filtered_operacoes_df = filtered_operacoes_df[filtered_operacoes_df['cripto'].isin(filter_crypto)]
        
        # Aplicar filtro de pesquisa de texto livre (prioriza display_name, depois symbol)
        if search_crypto_text:
            filtered_operacoes_df = filtered_operacoes_df[
                filtered_operacoes_df['cripto_display_name'].str.lower().str.contains(search_crypto_text) |
                filtered_operacoes_df['cripto'].str.lower().str.contains(search_crypto_text)
            ]

        if not filtered_operacoes_df.empty:
            # Exibir o formulário de edição se um ID de operação estiver definido
            if st.session_state.get("edit_operation_id"):
                edit_operation_id = st.session_state["edit_operation_id"]
                operation_to_edit = df_operacoes[df_operacoes['id'] == edit_operation_id].iloc[0]

                st.markdown("---")
                st.subheader(f"Editar Operação (ID: {edit_operation_id})")
                with st.form(key=f"form_edit_operacao_{edit_operation_id}"):
                    edited_tipo_operacao = st.selectbox(
                        "Tipo de Operação",
                        ["Compra", "Venda", "Deposito Fiat", "Saque Fiat", "Transferência Recebida", "Transferência Enviada"],
                        index=["Compra", "Venda", "Deposito Fiat", "Saque Fiat", "Transferência Recebida", "Transferência Enviada"].index(operation_to_edit['tipo_operacao']),
                        key=f"edited_tipo_operacao_{edit_operation_id}"
                    )
                    edited_data_operacao = st.date_input(
                        "Data da Operação", 
                        value=pd.to_datetime(operation_to_edit['data_operacao']).date(), 
                        key=f"edited_data_operacao_{edit_operation_id}"
                    )

                    edited_crypto_symbol = operation_to_edit['cripto'] # Pega o símbolo original
                    edited_crypto_display_name = operation_to_edit['cripto_display_name']
                    edited_crypto_image_url = operation_to_edit['cripto_image_url']

                    # Campos de edição para criptomoeda (similar ao registro)
                    if edited_tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"]:
                        st.markdown(f"**Criptomoeda atual:** {edited_crypto_display_name} ({edited_crypto_symbol})")
                        
                        edit_crypto_method = st.radio(
                            "Editar criptomoeda?",
                            ["Manter atual", "Pesquisar manualmente (símbolo)"],
                            key=f"edit_crypto_method_{edit_operation_id}",
                            horizontal=True
                        )

                        if edit_crypto_method == "Pesquisar manualmente (símbolo)":
                            new_manual_crypto_symbol = st.text_input("Novo Símbolo da Criptomoeda (Ex: BTC, ETH)", value=edited_crypto_symbol, key=f"new_manual_crypto_symbol_{edit_operation_id}").upper()
                            if new_manual_crypto_symbol:
                                crypto_row_edit = df_cryptos_prices[df_cryptos_prices['symbol'] == new_manual_crypto_symbol]
                                if not crypto_row_edit.empty:
                                    edited_crypto_symbol = crypto_row_edit.iloc[0]['symbol']
                                    edited_crypto_display_name = crypto_row_edit.iloc[0]['name'] # Atualiza com o nome da lista
                                    edited_crypto_image_url = crypto_row_edit.iloc[0]['image']
                                    st.success(f"Nova criptomoeda encontrada: {edited_crypto_display_name} ({edited_crypto_symbol})")
                                else:
                                    st.warning(f"Símbolo '{new_manual_crypto_symbol}' não encontrado na lista. Será usado como está.")
                                    edited_crypto_symbol = new_manual_crypto_symbol
                                    edited_crypto_display_name = f"Nome desconhecido para {new_manual_crypto_symbol}" # Nome padrão
                                    edited_crypto_image_url = "❓" # Imagem padrão
                        
                        edited_quantidade = st.number_input(
                            "Quantidade da Criptomoeda", 
                            min_value=0.00000001, 
                            format="%.8f", 
                            value=float(operation_to_edit['quantidade']), 
                            key=f"edited_quantidade_{edit_operation_id}"
                        )

                    edited_custo_total = 0.0
                    if edited_tipo_operacao in ["Compra", "Venda"]:
                        edited_custo_total = st.number_input(
                            "Custo Total (em BRL ou moeda base da carteira)", 
                            min_value=0.0, 
                            format="%.8f", 
                            value=float(operation_to_edit['custo_total']), 
                            key=f"edited_custo_total_{edit_operation_id}"
                        )
                    
                    edited_ptax_na_op = 0.0
                    if is_foreign_wallet and edited_tipo_operacao in ["Compra", "Venda"]:
                        edited_ptax_na_op = st.number_input(
                            "PTAX (para carteiras estrangeiras)", 
                            min_value=0.00000001, 
                            format="%.4f", 
                            value=float(operation_to_edit['ptax_na_op']), 
                            key=f"edited_ptax_na_op_{edit_operation_id}"
                        )

                    col_edit_submit, col_edit_cancel = st.columns([0.2, 0.8])
                    with col_edit_submit:
                        submit_edit = st.form_submit_button("Salvar Edição ✅")
                    with col_edit_cancel:
                        cancel_edit = st.form_submit_button("Cancelar Edição ❌")

                    if submit_edit:
                        # Validações similares às do registro
                        if edited_tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"] and not edited_crypto_symbol:
                            st.error("Por favor, selecione ou insira o símbolo da criptomoeda para esta operação.")
                        elif edited_quantidade <= 0 and edited_tipo_operacao in ["Compra", "Venda", "Transferência Recebida", "Transferência Enviada"]:
                            st.error("A quantidade da criptomoeda deve ser maior que zero.")
                        elif edited_custo_total <= 0 and edited_tipo_operacao in ["Compra", "Venda"]:
                            st.error("O custo total deve ser maior que zero para operações de compra/venda.")
                        elif is_foreign_wallet and edited_tipo_operacao in ["Compra", "Venda"] and edited_ptax_na_op <= 0:
                            st.error("Para carteiras estrangeiras, a PTAX deve ser maior que zero para operações de compra/venda.")
                        else:
                            edited_preco_medio_compra_na_op = 0.0
                            if edited_tipo_operacao in ["Compra", "Venda"] and edited_quantidade > 0:
                                edited_preco_medio_compra_na_op = edited_custo_total / edited_quantidade
                            
                            # Atualiza a linha no DataFrame original
                            idx_to_update = df_operacoes[df_operacoes['id'] == edit_operation_id].index[0]
                            df_operacoes.loc[idx_to_update, 'tipo_operacao'] = edited_tipo_operacao
                            df_operacoes.loc[idx_to_update, 'data_operacao'] = edited_data_operacao.strftime('%Y-%m-%d %H:%M:%S')
                            df_operacoes.loc[idx_to_update, 'cripto'] = edited_crypto_symbol
                            df_operacoes.loc[idx_to_update, 'cripto_display_name'] = edited_crypto_display_name
                            df_operacoes.loc[idx_to_update, 'cripto_image_url'] = edited_crypto_image_url
                            df_operacoes.loc[idx_to_update, 'quantidade'] = edited_quantidade
                            df_operacoes.loc[idx_to_update, 'custo_total'] = edited_custo_total
                            df_operacoes.loc[idx_to_update, 'preco_medio_compra_na_op'] = edited_preco_medio_compra_na_op
                            df_operacoes.loc[idx_to_update, 'ptax_na_op'] = edited_ptax_na_op

                            save_operacoes(df_operacoes)
                            st.success("Operação atualizada com sucesso!")
                            st.session_state["edit_operation_id"] = None # Fecha o formulário de edição
                            st.rerun()
                    elif cancel_edit:
                        st.session_state["edit_operation_id"] = None
                        st.info("Edição cancelada.")
                        st.rerun()

            # Tabela de operações
            st.dataframe(
                filtered_operacoes_df.style.format({
                    'quantidade': lambda x: format_number_br(x, 8),
                    'custo_total': format_currency_brl,
                    'preco_medio_compra_na_op': format_currency_brl,
                    'lucro_prejuizo_na_op': format_currency_brl,
                    'ptax_na_op': lambda x: format_number_br(x, 4) if x > 0 else '-'
                }),
                column_config={
                    "id": "ID da Operação",
                    "wallet_id": None, # Esconde ID da carteira
                    "cpf_usuario": None, # Esconde CPF
                    "tipo_operacao": "Tipo",
                    "cripto": "Símbolo Cripto",
                    "cripto_display_name": "Criptomoeda",
                    "cripto_image_url": st.column_config.ImageColumn(""), # Coluna para imagem da cripto
                    "quantidade": "Quantidade",
                    "custo_total": "Custo Total (BRL)",
                    "data_operacao": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm:ss"),
                    "preco_medio_compra_na_op": "Preço Médio (BRL/UN)",
                    "lucro_prejuizo_na_op": "Lucro/Prejuízo (BRL)",
                    "ptax_na_op": "PTAX (op. Estrangeira)",
                    "Ações": st.column_config.Column("Ações", width="small") # Coluna para botões de ação
                },
                hide_index=True,
                use_container_width=True,
                height=(len(filtered_operacoes_df) + 1) * 35 + 3 # Altura dinâmica
            )

            # Botões de ação por linha (abaixo da tabela para contornar limitações de callback do DataFrame)
            st.markdown("##### Ações por Operação")
            for _, op_row in filtered_operacoes_df.iterrows():
                col_op_id, col_op_edit, col_op_delete = st.columns([0.6, 0.2, 0.2])
                with col_op_id:
                    st.write(f"**ID:** `{op_row['id']}`")
                with col_op_edit:
                    if st.button("✏️ Editar", key=f"edit_op_btn_{op_row['id']}"):
                        st.session_state["edit_operation_id"] = op_row['id']
                        st.session_state["confirm_delete_operation_id"] = None # Garante que modal de delete não aparece
                        st.rerun() # Recarrega para mostrar o formulário de edição
                with col_op_delete:
                    if st.button("🗑️ Excluir", key=f"delete_op_btn_{op_row['id']}"):
                        st.session_state["confirm_delete_operation_id"] = op_row['id']
                        st.session_state["edit_operation_id"] = None # Garante que formulário de edição não aparece
                        st.rerun()
            
            # Modal de confirmação para exclusão de operação
            operation_confirm_placeholder = st.empty()
            if st.session_state.get('confirm_delete_operation_id'):
                with operation_confirm_placeholder.container():
                    op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
                    
                    st.markdown(f"""
                    <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                        <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
                        <p>Você tem certeza que deseja excluir a operação com ID:</p>
                        <p style="font-weight:bold;">`{op_to_confirm_delete_id}`</p>
                        <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível.</p>
                        <p>Deseja realmente continuar?</p>
                    </div>
                    """, unsafe_allow_html=True)

                    col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
                    with col_confirm_op:
                        if st.button("Sim, Excluir", key="confirm_operation_delete_btn_modal"):
                            df_operacoes_updated = df_operacoes[df_operacoes['id'] != op_to_confirm_delete_id]
                            save_operacoes(df_operacoes_updated)
                            st.success(f"Operação '{op_to_confirm_delete_id}' excluída com sucesso!")
                            st.session_state['confirm_delete_operation_id'] = None
                            operation_confirm_placeholder.empty()
                            st.rerun()
                    with col_cancel_op:
                        if st.button("Cancelar", key="cancel_operation_delete_btn_modal"):
                            st.session_state['confirm_delete_operation_id'] = None
                            operation_confirm_placeholder.empty()
                            st.rerun()
            else:
                operation_confirm_placeholder.empty()

        else:
            st.info("Nenhuma operação encontrada para esta carteira com os filtros aplicados.")
    else:
        st.info("Nenhuma operação registrada para esta carteira ainda.")
    
    st.markdown("---")
    st.subheader("Portfólio da Carteira")

    if not wallet_operacoes_df.empty:
        # Calcular saldo de criptos
        saldo_criptos = wallet_operacoes_df.groupby('cripto').apply(
            lambda x: (
                x[x['tipo_operacao'].isin(['Compra', 'Transferência Recebida'])]['quantidade'].sum() -
                x[x['tipo_operacao'].isin(['Venda', 'Transferência Enviada'])]['quantidade'].sum()
            )
        ).reset_index(name='saldo')
        saldo_criptos = saldo_criptos[saldo_criptos['saldo'] > 0] # Apenas criptos com saldo positivo

        if not saldo_criptos.empty:
            # Calcular custo médio de compra para cada cripto
            compras_df = wallet_operacoes_df[wallet_operacoes_df['tipo_operacao'] == 'Compra'].copy()
            if not compras_df.empty:
                custo_medio_por_cripto = compras_df.groupby('cripto').apply(
                    lambda x: x['custo_total'].sum() / x['quantidade'].sum()
                ).reset_index(name='custo_medio')

                # Unir com o saldo e adicionar preços atuais
                saldo_criptos = pd.merge(saldo_criptos, custo_medio_por_cripto, on='cripto', how='left')
            else:
                saldo_criptos['custo_medio'] = 0.0 # Se não houver compras, custo médio é 0

            # Adicionar nomes de exibição e URLs de imagem
            saldo_criptos = pd.merge(
                saldo_criptos, 
                df_cryptos_prices[['symbol', 'display_name', 'image']], 
                left_on='cripto', 
                right_on='symbol', 
                how='left'
            )
            # Preencher display_name e image para criptos não encontradas
            saldo_criptos['display_name'] = saldo_criptos['display_name'].fillna(saldo_criptos['cripto'].apply(lambda x: f"{x} - (Desconhecido)"))
            saldo_criptos['image'] = saldo_criptos['image'].fillna("❓")
            saldo_criptos.drop(columns=['symbol'], inplace=True) # Remove coluna 'symbol' duplicada

            saldo_criptos['preco_atual'] = saldo_criptos['cripto'].apply(lambda x: get_current_crypto_price(x, df_cryptos_prices))
            
            # Calcular valor atual e lucro/prejuízo
            saldo_criptos['valor_atual'] = saldo_criptos['saldo'] * saldo_criptos['preco_atual']
            saldo_criptos['lucro_prejuizo'] = (saldo_criptos['valor_atual'] - (saldo_criptos['saldo'] * saldo_criptos['custo_medio']))
            saldo_criptos['percentual_lucro_prejuizo'] = (saldo_criptos['lucro_prejuizo'] / (saldo_criptos['saldo'] * saldo_criptos['custo_medio'])) * 100
            
            # Tratar casos de divisão por zero ou custo médio zero para percentual
            saldo_criptos['percentual_lucro_prejuizo'] = saldo_criptos.apply(
                lambda row: (row['lucro_prejuizo'] / (row['saldo'] * row['custo_medio'])) * 100 
                if (row['saldo'] * row['custo_medio']) != 0 else 0, axis=1
            )
            
            # Exibir resumo do portfólio
            total_investido = (saldo_criptos['saldo'] * saldo_criptos['custo_medio']).sum()
            total_valor_atual = saldo_criptos['valor_atual'].sum()
            total_lucro_prejuizo = total_valor_atual - total_investido

            col_total1, col_total2, col_total3 = st.columns(3)
            with col_total1:
                st.metric("Total Investido", format_currency_brl(total_investido))
            with col_total2:
                st.metric("Valor Atual Total", format_currency_brl(total_valor_atual))
            with col_total3:
                st.metric("Lucro/Prejuízo Total", format_currency_brl(total_lucro_prejuizo))

            st.dataframe(
                saldo_criptos.style.format({
                    'saldo': lambda x: format_number_br(x, 8),
                    'custo_medio': format_currency_brl,
                    'preco_atual': format_currency_brl,
                    'valor_atual': format_currency_brl,
                    'lucro_prejuizo': format_currency_brl,
                    'percentual_lucro_prejuizo': lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
                }),
                column_config={
                    "cripto": "Símbolo",
                    "display_name": "Criptomoeda",
                    "image": st.column_config.ImageColumn(""), # Coluna para imagem da cripto
                    "saldo": "Saldo",
                    "custo_medio": "Custo Médio (BRL)",
                    "preco_atual": "Preço Atual (BRL)",
                    "valor_atual": "Valor Atual (BRL)",
                    "lucro_prejuizo": "Lucro/Prejuízo (BRL)",
                    "percentual_lucro_prejuizo": "Lucro/Prejuízo (%)"
                },
                hide_index=True,
                use_container_width=True
            )

        else:
            st.info("Nenhum saldo de criptomoedas positivo nesta carteira.")
    else:
        st.info("Nenhuma operação registrada para esta carteira ainda. O portfólio será exibido após o registro de operações.")

# --- Funções de Autenticação de Usuário ---

def show_register_page():
    """Exibe a página de registro de novo usuário."""
    st.title("Cadastre-se")

    with st.form("form_register"):
        name = st.text_input("Nome Completo")
        cpf = st.text_input("CPF (somente números)", max_chars=11, help="Utilizaremos seu CPF como identificador único para sua conta. Guarde-o bem, ele será o seu usuário.")
        phone = st.text_input("Telefone (com DDD)")
        email = st.text_input("Email")
        password = st.text_input("Crie uma Senha", type="password")
        confirm_password = st.text_input("Confirme a Senha", type="password")
        
        submitted = st.form_submit_button("Criar Conta")

        if submitted:
            df_users = load_users()
            if not name or not cpf or not phone or not email or not password or not confirm_password:
                st.error("Por favor, preencha todos os campos.")
            elif len(cpf) != 11 or not cpf.isdigit():
                st.error("CPF deve conter exatamente 11 dígitos numéricos.")
            elif df_users['cpf'].astype(str).str.contains(cpf).any():
                st.error("CPF já cadastrado. Tente fazer login ou recuperar sua senha.")
            elif password != confirm_password:
                st.error("As senhas não conferem.")
            else:
                new_user = pd.DataFrame([{
                    "cpf": cpf,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "password_hash": hash_password(password)
                }])
                save_users(pd.concat([df_users, new_user], ignore_index=True))
                st.success("Cadastro realizado com sucesso! Por favor, faça login.")
                st.session_state["auth_page"] = "login"
                st.rerun()

    if st.button("Já tem uma conta? Faça Login"):
        st.session_state["auth_page"] = "login"
        st.rerun()

def show_login_page():
    """Exibe a página de login de usuário."""
    st.title("Login")

    with st.form("form_login"):
        cpf = st.text_input("CPF (somente números)", max_chars=11)
        password = st.text_input("Senha", type="password")
        
        submitted = st.form_submit_button("Entrar")

        if submitted:
            df_users = load_users()
            user_row = df_users[df_users['cpf'] == cpf]
            
            if user_row.empty:
                st.error("CPF não encontrado.")
            elif hash_password(password) == user_row['password_hash'].iloc[0]:
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = cpf
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ainda não tem uma conta? Cadastre-se"):
            st.session_state["auth_page"] = "register"
            st.rerun()
    with col2:
        if st.button("Esqueci minha senha"):
            st.session_state["auth_page"] = "forgot_password"
            st.rerun()

def show_forgot_password_page():
    """Exibe a página de recuperação de senha."""
    st.title("Esqueci minha Senha")

    if "recovery_step" not in st.session_state:
        st.session_state["recovery_step"] = "email_input"

    if st.session_state["recovery_step"] == "email_input":
        with st.form("form_forgot_password_email"):
            st.info("Insira seu e-mail cadastrado para receber um código de recuperação.")
            email_for_recovery = st.text_input("Email", key="email_for_recovery")
            submitted_email = st.form_submit_button("Enviar Código")

            if submitted_email:
                df_users = load_users()
                user_row = df_users[df_users['email'] == email_for_recovery]
                if not user_row.empty:
                    st.session_state["temp_cpf_for_recovery"] = user_row['cpf'].iloc[0]
                    send_recovery_code(email_for_recovery)
                    st.session_state["recovery_step"] = "code_input"
                    st.rerun()
                else:
                    st.error("Email não encontrado em nossos registros.")
    
    elif st.session_state["recovery_step"] == "code_input":
        with st.form("form_forgot_password_code"):
            st.info("Digite o código de 6 dígitos que você recebeu no seu e-mail.")
            code_input = st.text_input("Código de Recuperação", max_chars=6, key="code_input_recovery")
            submitted_code = st.form_submit_button("Verificar Código")

            if submitted_code:
                if code_input == st.session_state.get("recovery_code"):
                    st.success("Código verificado com sucesso! Agora você pode redefinir sua senha.")
                    st.session_state["recovery_step"] = "reset_password"
                    st.rerun()
                else:
                    st.error("Código incorreto ou expirado. Por favor, tente novamente.")

    elif st.session_state["recovery_step"] == "reset_password":
        with st.form("form_reset_password"):
            st.info("Digite sua nova senha.")
            new_password = st.text_input("Nova Senha", type="password", key="new_password_reset")
            confirm_new_password = st.text_input("Confirme a Nova Senha", type="password", key="confirm_new_password_reset")
            submitted_reset = st.form_submit_button("Redefinir Senha")

            if submitted_reset:
                if new_password != confirm_new_password:
                    st.error("As senhas não conferem.")
                else:
                    df_users = load_users()
                    cpf_to_reset = st.session_state.get("temp_cpf_for_recovery")
                    df_users.loc[df_users['cpf'] == cpf_to_reset, 'password_hash'] = hash_password(new_password)
                    save_users(df_users)
                    st.success("Senha redefinida com sucesso! Faça login com sua nova senha.")
                    # Limpar estados de recuperação e voltar para login
                    del st.session_state["recovery_step"]
                    del st.session_state["recovery_code"]
                    del st.session_state["reset_email"]
                    del st.session_state["temp_cpf_for_recovery"]
                    st.session_state["auth_page"] = "login"
                    st.rerun()
    
    if st.session_state["recovery_step"] != "email_input":
        if st.button("Voltar ao Início de Recuperação", key="btn_voltar_esqueci"):
            st.session_state["recovery_step"] = "email_input"
            if "recovery_code" in st.session_state: del st.session_state["recovery_code"]
            if "reset_email" in st.session_state: del st.session_state["reset_email"]
            if "temp_cpf_for_recovery" in st.session_state: del st.session_state["temp_cpf_for_recovery"]
            st.rerun()

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
# Novo estado para a confirmação de exclusão de conta
if 'confirm_delete_account' not in st.session_state:
    st.session_state['confirm_delete_account'] = False
# Novo estado para verificar se a senha da exclusão de conta foi validada
if 'delete_account_password_verified' not in st.session_state:
    st.session_state['delete_account_password_verified'] = False
# Novo estado para edição de operação
if 'edit_operation_id' not in st.session_state:
    st.session_state['edit_operation_id'] = None

if st.session_state["logged_in"]:
    show_dashboard()
else:
    if st.session_state["auth_page"] == "login":
        show_login_page()
    elif st.session_state["auth_page"] == "register":
        show_register_page()
    elif st.session_state["auth_page"] == "forgot_password":
        show_forgot_password_page()
