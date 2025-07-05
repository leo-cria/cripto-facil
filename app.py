import streamlit as st
import pandas as pd
import hashlib
import os
import random
import string
import uuid
from datetime import datetime, date, time
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
                st.session_state["edit_operation_id"] = None # Resetar estado de edição
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
            st.session_state["edit_operation_id"] = None # Resetar estado de edição
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
                    <h4 style="color:#ff0000; margin-top:0;'>🛑 CONFIRMAR EXCLUSÃO DA CONTA</h4>
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
                        st.session_state["edit_operation_id"] = None # Resetar estado de edição
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
                            st.session_state["confirm_delete_account"] = False # Resetar estado de exclusão de conta
                            st.session_state["edit_operation_id"] = None # Resetar estado de edição
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
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ CONFIRMAR EXCLUSÃO DE CARTEIRA</h4>
                    <p style="font-weight:bold;">Você tem certeza que deseja excluir a carteira <strong>"{wallet_name}"</strong>?</p>
                    <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível e também excluirá TODAS as operações vinculadas a esta carteira!</p>
                    <p>Deseja realmente continuar?</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_wallet, col_cancel_wallet = st.columns([0.2, 0.8])
                with col_confirm_wallet:
                    if st.button("SIM, EXCLUIR", key="confirm_wallet_delete_btn_modal"):
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
            'index': 'Cripto_Symbol',         # O símbolo original da cripto (do índice)
            'display_name': 'Cripto',         # O display_name da cripto
            'image': 'Logo',                # A URL da imagem ou emoji (RENOMEADO)
            'quantidade': 'Quantidade',       # A quantidade atual
            'custo_total': 'Custo Total',     # O custo total
            'custo_medio': 'Custo Médio',     # O custo médio
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
            st.markdown(f"<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Atualizado em: {updated_dt.strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
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
        st.markdown("---")

        for idx, row in portfolio_df.iterrows():
            cols_portfolio = st.columns(cols_ratio_portfolio)
            with cols_portfolio[0]: # Coluna Logo
                if row['Logo'] == "🪙": # Se for o emoji, exibe o emoji
                    st.markdown("🪙", unsafe_allow_html=True)
                elif row['Logo']:
                    st.markdown(f"<img src='{row['Logo']}' width='24' height='24'>", unsafe_allow_html=True)
                else:
                    st.write("➖")
            with cols_portfolio[1]: # Coluna Cripto
                st.write(row['Cripto'])
            with cols_portfolio[2]: # Formatar a quantidade com ponto e vírgula do Brasil
                st.write(format_number_br(row['Quantidade'], decimals=8))
            with cols_portfolio[3]: # Custo Total
                st.write(format_currency_brl(row['Custo Total']))
            with cols_portfolio[4]: # Lucro Realizado
                color = "green" if row['Lucro Realizado'] >= 0 else "red"
                st.markdown(f"<span style='color:{color}'>{format_currency_brl(row['Lucro Realizado'])}</span>", unsafe_allow_html=True)
            with cols_portfolio[5]: # Valor Atual da Posição
                st.write(format_currency_brl(row['Valor Atual da Posição']))
            with cols_portfolio[6]: # POSIÇÃO
                st.write(f"{format_number_br(row['POSIÇÃO'], decimals=2)}%")
            st.markdown("---")
    else:
        st.info("Sua carteira não possui criptomoedas atualmente (todas as compras foram compensadas por vendas ou não há operações registradas com saldo positivo).")
    st.markdown("---")

    # --- Seção de cadastro de nova operação dentro de um expander ---
    with st.expander("➕ Cadastrar Nova Operação", expanded=False): # MODIFICADO: expanded=False
        if 'current_tipo_operacao' not in st.session_state:
            st.session_state['current_tipo_operacao'] = "Compra"
        tipo_operacao_display = st.radio(
            "Tipo de Operação",
            ["Compra", "Venda"],
            horizontal=True,
            key="tipo_op_radio_external",
            index=["Compra", "Venda"].index(st.session_state['current_tipo_operacao'])
        )
        st.session_state['current_tipo_operacao'] = tipo_operacao_display # Garante que o estado é atualizado

        # Carrega a lista de dicionários de criptomoedas
        _, cryptocurrencies_data_df = load_cryptocurrencies_from_file()

        # Cria uma lista de strings para exibição no selectbox (apenas o display_name)
        display_options = cryptocurrencies_data_df['display_name'].tolist()

        # Mapeia o display_name para o objeto completo da criptomoeda para fácil recuperação
        display_name_to_crypto_map = {crypto['display_name']: crypto for crypto in cryptocurrencies_data_df.to_dict('records')}

        # Inicializa o estado para a opção selecionada no selectbox
        # Garante que a opção selecionada esteja sempre na lista de opções válidas
        if 'selected_crypto_display_name' not in st.session_state or st.session_state['selected_crypto_display_name'] not in display_options:
            st.session_state['selected_crypto_display_name'] = display_options[0] if display_options else None
        
        # Callback para o selectbox
        def handle_crypto_select_change():
            # Removido 'selected_value' como argumento
            st.session_state['selected_crypto_display_name'] = st.session_state.cripto_select_outside_form # O selectbox exibirá as strings de display_name

        selected_display_name = st.selectbox(
            "Criptomoeda",
            options=display_options, # Usa apenas as opções da API
            key="cripto_select_outside_form",
            help="Selecione a criptomoeda para a operação.",
            index=display_options.index(st.session_state['selected_crypto_display_name']) if st.session_state['selected_crypto_display_name'] in display_options else 0,
            on_change=handle_crypto_select_change # Removido 'args'
        )

        cripto_symbol = ""
        selected_crypto_for_display = None
        # --- Lógica simplificada para obter a cripto selecionada ---
        if selected_display_name:
            selected_crypto_for_display = display_name_to_crypto_map.get(selected_display_name)
            if selected_crypto_for_display:
                cripto_symbol = selected_crypto_for_display['symbol']
            else:
                # Fallback se por algum motivo a cripto não for encontrada no mapa (improvável com a nova lógica)
                cripto_symbol = ""
                st.error("Criptomoeda selecionada não encontrada na lista de dados.")

        # Exibe a logo e o nome completo da criptomoeda selecionada
        if selected_crypto_for_display:
            # Verifica se a imagem da API é válida ou se é o emoji padrão
            if selected_crypto_for_display['image'] and selected_crypto_for_display['image'] != "🪙":
                st.markdown(
                    f"<img src='{selected_crypto_for_display['image']}' width='24' height='24' style='vertical-align:middle; margin-right: 5px;'> "
                    f"<span style='font-size:1.1em; font-weight:bold;'>{selected_crypto_for_display['name']} ({selected_crypto_for_display['symbol'].upper()})</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<span>🪙 {selected_crypto_for_display['name']} ({selected_crypto_for_display['symbol'].upper()})</span>",
                    unsafe_allow_html=True
                )
        
        # Obter o preço atual para exibir
        current_price_for_display = get_current_crypto_price(cripto_symbol, cryptocurrencies_data_df)
        st.info(f"Preço atual de {selected_display_name}: {format_currency_brl(current_price_for_display)}")

        with st.form("form_add_operation"):
            quantidade = st.number_input("Quantidade", min_value=0.00000001, format="%.8f", key="quantidade_add_op")
            custo_total = st.number_input("Custo Total (BRL)", min_value=0.01, format="%.2f", key="custo_total_add_op")
            data_op = st.date_input("Data da Operação", value="today", key="data_op_add_op")
            hora_op = st.time_input("Hora da Operação", value="now", key="hora_op_add_op")

            submitted_op = st.form_submit_button("Registrar Operação ➕")

            if submitted_op:
                if not selected_display_name or not cripto_symbol:
                    st.error("Por favor, selecione uma criptomoeda válida.")
                elif quantidade <= 0 or custo_total <= 0:
                    st.error("Quantidade e Custo Total devem ser maiores que zero.")
                else:
                    data_e_hora_operacao = datetime.combine(data_op, hora_op)

                    # Calcula preco_medio_compra_na_op apenas para compras
                    preco_medio_compra_na_op = 0.0
                    if tipo_operacao_display == 'Compra':
                        preco_medio_compra_na_op = custo_total / quantidade
                    
                    # Para vendas, o lucro/prejuízo será calculado posteriormente
                    lucro_prejuizo_na_op = 0.0 # Inicializa como 0.0, será calculado após a compra

                    # Ptax para carteiras estrangeiras
                    ptax_na_op = float('nan')
                    if is_foreign_wallet:
                        # TODO: Implementar a busca do PTAX do dia da operação
                        # Por enquanto, um valor placeholder ou buscar de uma API real.
                        # Exemplo: ptax_na_op = buscar_ptax_do_dia(data_op)
                        ptax_na_op = 5.0 # Valor placeholder para demonstração

                    nova_operacao = pd.DataFrame([{
                        "id": f"operacao_{uuid.uuid4()}",
                        "wallet_id": wallet_id,
                        "cpf_usuario": user_cpf,
                        "tipo_operacao": tipo_operacao_display,
                        "cripto": cripto_symbol,
                        "quantidade": quantidade,
                        "custo_total": custo_total,
                        "data_operacao": data_e_hora_operacao,
                        "preco_medio_compra_na_op": preco_medio_compra_na_op,
                        "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                        "ptax_na_op": ptax_na_op,
                        "cripto_display_name": selected_display_name, # Salva o display_name
                        "cripto_image_url": selected_crypto_for_display['image'] if selected_crypto_for_display else "🪙" # Salva a URL da imagem
                    }])

                    current_operacoes_df = load_operacoes()
                    
                    # --- Lógica de cálculo de lucro/prejuízo para vendas (após carregar dados existentes) ---
                    if tipo_operacao_display == 'Venda':
                        # Para calcular o lucro/prejuízo de uma venda, precisamos do custo médio de compra
                        # das unidades vendidas. Isso geralmente envolve um método como FIFO, LIFO, ou Custo Médio.
                        # Aqui, faremos uma simplificação para fins de demonstração:
                        # Assumimos que a `preco_medio_compra_na_op` para vendas representará o custo médio
                        # das unidades que estão sendo vendidas, baseado no histórico da carteira.

                        # Carregar apenas operações de COMPRA para a mesma cripto e carteira
                        compras_anteriores = current_operacoes_df[
                            (current_operacoes_df['wallet_id'] == wallet_id) &
                            (current_operacoes_df['cpf_usuario'] == user_cpf) &
                            (current_operacoes_df['cripto'] == cripto_symbol) &
                            (current_operacoes_df['tipo_operacao'] == 'Compra')
                        ]
                        
                        # Calcula o custo médio ponderado de todas as compras daquela cripto na carteira
                        if not compras_anteriores.empty and compras_anteriores['quantidade'].sum() > 0:
                            custo_total_compras = (compras_anteriores['quantidade'] * compras_anteriores['preco_medio_compra_na_op']).sum()
                            quantidade_total_compras = compras_anteriores['quantidade'].sum()
                            custo_medio_ponderado_geral = custo_total_compras / quantidade_total_compras
                            
                            # O lucro/prejuízo na venda é (preço_de_venda_por_unidade - custo_medio_ponderado) * quantidade_vendida
                            preco_venda_por_unidade = custo_total / quantidade
                            nova_operacao.loc[0, 'preco_medio_compra_na_op'] = custo_medio_ponderado_geral # Armazena o custo médio na op de venda
                            nova_operacao.loc[0, 'lucro_prejuizo_na_op'] = (preco_venda_por_unidade - custo_medio_ponderado_geral) * quantidade
                        else:
                            st.warning("Não há compras anteriores desta criptomoeda para calcular o lucro/prejuízo da venda. Lucro/prejuízo definido como 0.")
                            nova_operacao.loc[0, 'lucro_prejuizo_na_op'] = 0.0

                    save_operacoes(pd.concat([current_operacoes_df, nova_operacao], ignore_index=True))
                    st.success("Operação registrada com sucesso!")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações")

    df_operacoes = load_operacoes()
    wallet_ops = df_operacoes[
        (df_operacoes['wallet_id'] == wallet_id) &
        (df_operacoes['cpf_usuario'] == user_cpf)
    ].sort_values(by="data_operacao", ascending=False).reset_index(drop=True)

    if not wallet_ops.empty:
        # Exibir a tabela com as operações
        # Definir as colunas e suas proporções
        col_ratios = [0.05, 0.07, 0.05, 0.13, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        cols = st.columns(col_ratios)
        headers = ["", "Tipo", "Cripto", "Data", "Quantidade", "Custo Total", "Preço Médio Compra", "Lucro/Prejuízo", "PTAX", "Ações", ""]
        for i, header in enumerate(headers):
            with cols[i]:
                st.markdown(f"**{header}**")
        st.markdown("---")

        for idx, op in wallet_ops.iterrows():
            op_id = op['id']
            cols = st.columns(col_ratios)

            if st.session_state.get('edit_operation_id') == op_id:
                # --- INÍCIO DO FORMULÁRIO DE EDIÇÃO ---
                st.subheader(f"Editar Operação {op_id}")
                with st.form(key=f"form_edit_operation_{op_id}"):
                    # Recupera a operação a ser editada
                    op_to_edit_data = wallet_ops[wallet_ops['id'] == op_id].iloc[0]

                    # Campos de edição preenchidos com os valores atuais da operação
                    edited_tipo_op = st.radio(
                        "Tipo de Operação",
                        ["Compra", "Venda"],
                        horizontal=True,
                        key=f"edit_tipo_op_{op_id}",
                        index=["Compra", "Venda"].index(op_to_edit_data['tipo_operacao'])
                    )

                    # Carrega a lista de criptomoedas para ter os display_names e símbolos
                    _, cryptocurrencies_data_df_edit = load_cryptocurrencies_from_file()
                    display_options_edit = cryptocurrencies_data_df_edit['display_name'].tolist()
                    display_name_to_crypto_map_edit = {crypto['display_name']: crypto for crypto in cryptocurrencies_data_df_edit.to_dict('records')}

                    # Inicializa o selected_crypto_display_name para a cripto da operação, se válido
                    initial_crypto_display_name_edit = op_to_edit_data.get('cripto_display_name', '')
                    if initial_crypto_display_name_edit not in display_options_edit and display_options_edit:
                        initial_crypto_display_name_edit = display_options_edit[0] # Fallback para a primeira opção se a original não estiver na lista

                    edited_crypto_display_name = st.selectbox(
                        "Criptomoeda",
                        options=display_options_edit,
                        key=f"edit_crypto_select_{op_id}",
                        index=display_options_edit.index(initial_crypto_display_name_edit) if initial_crypto_display_name_edit in display_options_edit else 0,
                        help="Selecione a criptomoeda para a operação."
                    )
                    # Encontra o símbolo da cripto selecionada para salvar
                    edited_cripto_symbol = ""
                    selected_crypto_obj_edit = display_name_to_crypto_map_edit.get(edited_crypto_display_name)
                    if selected_crypto_obj_edit:
                        edited_cripto_symbol = selected_crypto_obj_edit['symbol']
                    
                    # Quantidade (campo editável)
                    edited_quantity = st.number_input(
                        "Quantidade",
                        min_value=0.0,
                        value=float(op_to_edit_data['quantidade']),
                        format="%.8f",
                        key=f"edit_quantity_{op_id}"
                    )

                    # Custo Total (campo editável)
                    edited_cost = st.number_input(
                        "Custo Total (BRL)",
                        min_value=0.0,
                        value=float(op_to_edit_data['custo_total']),
                        format="%.2f",
                        key=f"edit_cost_{op_id}"
                    )

                    # Data e Hora (campos editáveis)
                    current_dt_op = op_to_edit_data['data_operacao']
                    # Garante que 'value' para date_input e time_input são os tipos corretos
                    edited_date = st.date_input("Data da Operação", value=current_dt_op.date(), key=f"edit_date_{op_id}")
                    edited_time = st.time_input("Hora da Operação", value=current_dt_op.time(), key=f"edit_time_{op_id}")

                    # Botão de submissão do formulário de edição
                    edited_submitted = st.form_submit_button("Confirmar Edição ✅", key=f"submit_edit_op_{op_id}")

                # --- FIM DO FORMULÁRIO DE EDIÇÃO ---

                if edited_submitted:
                    # Lógica para processar as informações editadas
                    # Converta a data e hora editadas de volta para datetime
                    edited_datetime = datetime.combine(edited_date, edited_time)

                    # Atualiza o DataFrame de operações
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'tipo_operacao'] = edited_tipo_op
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'cripto'] = edited_cripto_symbol
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'cripto_display_name'] = edited_crypto_display_name
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'quantidade'] = edited_quantity
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'custo_total'] = edited_cost
                    df_operacoes.loc[df_operacoes['id'] == op_id, 'data_operacao'] = edited_datetime

                    # Recalcular preco_medio_compra_na_op, lucro_prejuizo_na_op
                    if edited_tipo_op == 'Compra':
                        if edited_quantity > 0:
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'preco_medio_compra_na_op'] = edited_cost / edited_quantity
                        else:
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'preco_medio_compra_na_op'] = 0.0
                        df_operacoes.loc[df_operacoes['id'] == op_id, 'lucro_prejuizo_na_op'] = 0.0 # Uma compra não tem lucro/prejuízo imediato

                    elif edited_tipo_op == 'Venda':
                        # Recalcular lucro/prejuízo da venda
                        compras_anteriores_para_calculo = df_operacoes[
                            (df_operacoes['wallet_id'] == wallet_id) &
                            (df_operacoes['cpf_usuario'] == user_cpf) &
                            (df_operacoes['cripto'] == edited_cripto_symbol) &
                            (df_operacoes['tipo_operacao'] == 'Compra')
                        ]
                        if not compras_anteriores_para_calculo.empty and compras_anteriores_para_calculo['quantidade'].sum() > 0:
                            custo_total_compras_calc = (compras_anteriores_para_calculo['quantidade'] * compras_anteriores_para_calculo['preco_medio_compra_na_op']).sum()
                            quantidade_total_compras_calc = compras_anteriores_para_calculo['quantidade'].sum()
                            custo_medio_ponderado_calc = custo_total_compras_calc / quantidade_total_compras_calc
                            
                            preco_venda_por_unidade_calc = edited_cost / edited_quantity
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'preco_medio_compra_na_op'] = custo_medio_ponderado_calc # Armazena o custo médio
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'lucro_prejuizo_na_op'] = (preco_venda_por_unidade_calc - custo_medio_ponderado_calc) * edited_quantity
                        else:
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'lucro_prejuizo_na_op'] = 0.0
                            df_operacoes.loc[df_operacoes['id'] == op_id, 'preco_medio_compra_na_op'] = 0.0

                    # Recalcular PTAX se for carteira estrangeira
                    if is_foreign_wallet:
                        # TODO: Chamar função para obter PTAX atualizado para a nova data
                        # df_operacoes.loc[df_operacoes['id'] == op_id, 'ptax_na_op'] = buscar_ptax_do_dia(edited_date)
                        df_operacoes.loc[df_operacoes['id'] == op_id, 'ptax_na_op'] = 5.0 # Valor placeholder
                    else:
                        df_operacoes.loc[df_operacoes['id'] == op_id, 'ptax_na_op'] = float('nan') # Remove PTAX se a carteira não for estrangeira

                    save_operacoes(df_operacoes) # Salva as operações atualizadas
                    st.success("Operação editada com sucesso!")
                    st.session_state['edit_operation_id'] = None # Sai do modo de edição
                    st.rerun() # Recarrega a página para mostrar as alterações

                if st.button("Cancelar Edição", key=f"cancel_edit_op_{op_id}"):
                    st.session_state['edit_operation_id'] = None # Sai do modo de edição
                    st.info("Edição cancelada.")
                    st.rerun()
            else:
                # Exibir operação normalmente
                with cols[0]:
                    st.markdown(f"<img src='{op['cripto_image_url']}' width='24' height='24'>", unsafe_allow_html=True)
                with cols[1]:
                    st.write(op['tipo_operacao'])
                with cols[2]:
                    st.write(op['cripto'])
                with cols[3]:
                    st.write(op['data_operacao'].strftime('%d/%m/%Y %H:%M'))
                with cols[4]:
                    st.write(format_number_br(op['quantidade'], decimals=8))
                with cols[5]:
                    st.write(format_currency_brl(op['custo_total']))
                with cols[6]:
                    st.write(format_currency_brl(op['preco_medio_compra_na_op']))
                with cols[7]:
                    color = "green" if op['lucro_prejuizo_na_op'] >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>{format_currency_brl(op['lucro_prejuizo_na_op'])}</span>", unsafe_allow_html=True)
                with cols[8]:
                    if pd.notna(op['ptax_na_op']):
                        st.write(format_number_br(op['ptax_na_op'], decimals=4))
                    else:
                        st.write("-")
                
                with cols[9]: # Coluna Ações
                    col_edit_btn, col_del_btn = st.columns(2)
                    with col_edit_btn:
                        if st.button("✏️", key=f"edit_op_btn_{op_id}"):
                            st.session_state['edit_operation_id'] = op_id
                            st.rerun()
                    with col_del_btn:
                        if st.button("🗑️", key=f"del_op_btn_{op_id}"):
                            st.session_state['confirm_delete_operation_id'] = op_id
                            st.rerun()
                with cols[10]: # Coluna vazia para alinhamento se necessário
                    pass
                st.markdown("---")
        
        # Modal de confirmação de exclusão de operação
        op_confirm_placeholder = st.empty()
        if st.session_state.get('confirm_delete_operation_id'):
            with op_confirm_placeholder.container():
                op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
                op_details = wallet_ops[wallet_ops['id'] == op_to_confirm_delete_id].iloc[0]
                
                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ CONFIRMAR EXCLUSÃO DE OPERAÇÃO</h4>
                    <p style="font-weight:bold;">Você tem certeza que deseja excluir a operação de {op_details['tipo_operacao']} de {op_details['quantidade']} {op_details['cripto_display_name']} ({op_details['cripto'].upper()}) realizada em {op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}?</p>
                    <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível.</p>
                    <p>Deseja realmente continuar?</p>
                </div>
                """, unsafe_allow_html=True)

                col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
                with col_confirm_op:
                    if st.button("SIM, EXCLUIR", key="confirm_op_delete_btn_modal"):
                        df_operacoes_updated = df_operacoes[df_operacoes['id'] != op_to_confirm_delete_id]
                        save_operacoes(df_operacoes_updated)
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
            op_confirm_placeholder.empty() # Garante que o placeholder está vazio se não houver confirmação

    else:
        st.info("Nenhuma operação registrada para esta carteira ainda.")
    st.markdown("---") # Fim da seção de histórico de operações

# --- Páginas de autenticação ---
def show_login_page():
    st.title("Bem-vindo ao Cripto Fácil!")
    st.subheader("Faça login para continuar")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        login_button = st.form_submit_button("Entrar")

        if login_button:
            df_users = load_users()
            user_found = df_users[(df_users['email'] == email) & (df_users['password_hash'] == hash_password(password))]
            if not user_found.empty:
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = user_found.iloc[0]['cpf']
                st.session_state["username"] = user_found.iloc[0]['name']
                st.session_state["pagina_atual"] = "Portfólio" # Redireciona para o dashboard principal
                st.success(f"Bem-vindo(a), {st.session_state['username']}!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")

    st.markdown("---")
    if st.button("Não tem uma conta? Registre-se aqui"):
        st.session_state["auth_page"] = "register"
        st.rerun()
    if st.button("Esqueceu sua senha?"):
        st.session_state["auth_page"] = "forgot_password"
        st.rerun()

def show_register_page():
    st.title("Registrar Nova Conta")

    with st.form("register_form"):
        cpf = st.text_input("CPF (apenas números)", max_chars=11)
        name = st.text_input("Nome Completo")
        phone = st.text_input("Telefone (com DDD)")
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirme a Senha", type="password")
        register_button = st.form_submit_button("Registrar")

        if register_button:
            df_users = load_users()
            if not cpf.isdigit() or len(cpf) != 11:
                st.error("CPF inválido. Deve conter 11 dígitos numéricos.")
            elif df_users['cpf'].isin([cpf]).any():
                st.error("CPF já cadastrado.")
            elif df_users['email'].isin([email]).any():
                st.error("Email já cadastrado.")
            elif password != confirm_password:
                st.error("As senhas não coincidem.")
            else:
                new_user = pd.DataFrame([{
                    "cpf": cpf,
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "password_hash": hash_password(password)
                }])
                save_users(pd.concat([df_users, new_user], ignore_index=True))
                st.success("Conta registrada com sucesso! Faça login.")
                st.session_state["auth_page"] = "login"
                st.rerun()

    st.markdown("---")
    if st.button("Voltar para o Login"):
        st.session_state["auth_page"] = "login"
        st.rerun()

def show_forgot_password_page():
    st.title("Recuperar Senha")

    if "recovery_stage" not in st.session_state:
        st.session_state["recovery_stage"] = "email_input"
        st.session_state["recovery_code"] = None
        st.session_state["reset_email"] = None

    if st.session_state["recovery_stage"] == "email_input":
        st.subheader("Digite seu email para recuperar a senha")
        with st.form("forgot_password_email_form"):
            email_input = st.text_input("Email cadastrado")
            send_code_button = st.form_submit_button("Enviar Código de Recuperação")

            if send_code_button:
                df_users = load_users()
                if df_users['email'].isin([email_input]).any():
                    send_recovery_code(email_input)
                    st.session_state["recovery_stage"] = "code_input"
                    st.rerun()
                else:
                    st.error("Email não encontrado.")

    elif st.session_state["recovery_stage"] == "code_input":
        st.subheader(f"Digite o código de 6 dígitos enviado para {st.session_state['reset_email']}")
        with st.form("forgot_password_code_form"):
            code_input = st.text_input("Código de Recuperação")
            verify_code_button = st.form_submit_button("Verificar Código")

            if verify_code_button:
                if code_input == st.session_state["recovery_code"]:
                    st.success("Código verificado com sucesso!")
                    st.session_state["recovery_stage"] = "new_password"
                    st.rerun()
                else:
                    st.error("Código incorreto. Tente novamente.")

    elif st.session_state["recovery_stage"] == "new_password":
        st.subheader("Defina sua nova senha")
        with st.form("forgot_password_new_password_form"):
            new_password = st.text_input("Nova Senha", type="password")
            confirm_new_password = st.text_input("Confirme a Nova Senha", type="password")
            reset_password_button = st.form_submit_button("Redefinir Senha")

            if reset_password_button:
                if new_password != confirm_new_password:
                    st.error("As senhas não coincidem.")
                else:
                    df_users = load_users()
                    email_to_reset = st.session_state["reset_email"]
                    df_users.loc[df_users['email'] == email_to_reset, 'password_hash'] = hash_password(new_password)
                    save_users(df_users)
                    st.success("Senha redefinida com sucesso! Faça login com sua nova senha.")
                    st.session_state["auth_page"] = "login"
                    st.session_state["recovery_stage"] = "email_input" # Reseta o fluxo
                    st.session_state["recovery_code"] = None
                    st.session_state["reset_email"] = None
                    st.rerun()
    
    st.markdown("---")
    if st.button("Voltar para o Login"):
        st.session_state["auth_page"] = "login"
        st.session_state["recovery_stage"] = "email_input" # Reseta o fluxo
        st.session_state["recovery_code"] = None
        st.session_state["reset_email"] = None
        st.rerun()

# --- Main App Logic ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = "login"

# Inicialização de estados para controle de UI
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
# Novo estado para controlar a edição de operações
if 'edit_operation_id' not in st.session_state:
    st.session_state['edit_operation_id'] = None
# Estados para os seletores de edição (precisam ser re-inicializados quando a edição começa)
# Adicionei 'last_edited_op_id' para saber quando resetar esses estados
if 'edit_op_type' not in st.session_state:
    st.session_state['edit_op_type'] = "Compra" # Default
if 'edit_crypto_display_name' not in st.session_state:
    st.session_state['edit_crypto_display_name'] = "" # Default vazio
if 'last_edited_op_id' not in st.session_state:
    st.session_state['last_edited_op_id'] = None # Para controlar o reset dos campos de edição


# A lógica de persistência de login é a maneira como você inicializa 'st.session_state["logged_in"]'
# Isso geralmente é feito por meio de um cookie seguro ou um sistema de token em uma aplicação real.
# Para esta aplicação Streamlit simples, a sessão do navegador mantém o estado.

if st.session_state["logged_in"]:
    show_dashboard()
else:
    if st.session_state["auth_page"] == "login":
        show_login_page()
    elif st.session_state["auth_page"] == "register":
        show_register_page()
    elif st.session_state["auth_page"] == "forgot_password":
        show_forgot_password_page()
