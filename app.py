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
        
        # Garante que a coluna 'cripto_display_name' exista
        if 'cripto_display_name' not in df.columns:
            df['cripto_display_name'] = "" # Ou um valor padrão mais adequado
        else:
            df['cripto_display_name'] = df['cripto_display_name'].astype(str).replace('nan', '')

        # Garante que a coluna 'cripto_image_url' exista
        if 'cripto_image_url' not in df.columns:
            df['cripto_image_url'] = "" # Ou um valor padrão mais adequado, como "🪙"
        else:
            df['cripto_image_url'] = df['cripto_image_url'].astype(str).replace('nan', '')


        return df
    return pd.DataFrame(columns=[
        "id", "wallet_id", "cpf_usuario", "tipo_operacao", "cripto",
        "quantidade", "custo_total", "data_operacao",
        "preco_medio_compra_na_op",
        "lucro_prejuizo_na_op",
        "ptax_na_op",
        "cripto_display_name", # Adicionada nova coluna (presente no original)
        "cripto_image_url" # Adicionada nova coluna (presente no original)
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
                    # Preenche NaN com 0.0 para garantir que o preço seja numérico
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

        # REMOVIDO A CAIXA DE MARKDOWN AQUI
        st.markdown("### Criar nova carteira") # Título direto, sem a caixa

        tipo_selecionado_criar = st.radio(
            "Tipo de carteira",
            ["Auto Custódia", "Corretora", "Banco"], # Adicionado 'Banco'
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
                pass # Não é necessário info1/info2 para corretora neste formulário simplificado
            elif tipo_selecionado_criar == "Banco": # NOVO: Campos para tipo "Banco"
                nome_input_criar = st.selectbox("Instituição Financeira", ["NUBANK", "ITAU", "MERCADO PAGO", "BRADESCO"], key="banco_selector_criar")


            nacional_input_criar = st.radio("Origem da carteira:", ["Nacional", "Estrangeira"], key="nacionalidade_radio_field_criar")

            enviado_criar = st.form_submit_button("Criar carteira ➕")
            if enviado_criar:
                if tipo_selecionado_criar == "Auto Custódia" and (not nome_input_criar or not info1_input_criar):
                    st.error("Por favor, preencha todos os campos obrigatórios para Auto Custódia.")
                elif (tipo_selecionado_criar == "Corretora" or tipo_selecionado_criar == "Banco") and not nome_input_criar:
                    st.error("Por favor, selecione uma opção para o tipo de carteira selecionado.")
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
                    # Para o tipo "Banco", não há info1/info2 específicas para exibir aqui, o "nome" já mostra a instituição.

                    col_access, col_delete = st.columns(2)

                    with col_access:
                        if st.button(f"Acessar Carteira ➡️", key=f"access_carteira_btn_{row['id']}"):
                            st.session_state["accessed_wallet_id"] = row['id']
                            st.session_state["pagina_atual"] = "Detalhes da Carteira"
                            st.session_state["confirm_delete_wallet_id"] = None
                            st.session_state["confirm_delete_operation_id"] = None
                            st.session_state["confirm_delete_account"] = False # Resetar estado de exclusão de conta
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

    # --- Seção de cadastro de nova operação (sem expander) ---
    st.markdown("#### Cadastrar Nova Operação")
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
    if 'selected_crypto_display_name' not in st.session_state or st.session_state['selected_crypto_display_name'] not in display_options:
        st.session_state['selected_crypto_display_name'] = display_options[0] if display_options else None
    
    # Callback para o selectbox
    def handle_crypto_select_change(): 
        st.session_state['selected_crypto_display_name'] = st.session_state.cripto_select_outside_form

    # O selectbox exibirá as strings de display_name
    selected_display_name = st.selectbox(
        "Criptomoeda", 
        options=display_options,
        key="cripto_select_outside_form",
        help="Selecione a criptomoeda para a operação.",
        index=display_options.index(st.session_state['selected_crypto_display_name']) if st.session_state['selected_crypto_display_name'] in display_options else 0,
        on_change=handle_crypto_select_change
    )

    cripto_symbol = ""
    selected_crypto_for_display = None
    
    if selected_display_name:
        selected_crypto_for_display = display_name_to_crypto_map.get(selected_display_name)
        if selected_crypto_for_display:
            cripto_symbol = selected_crypto_for_display['symbol']
        else:
            cripto_symbol = ""
            st.error("Criptomoeda selecionada não encontrada na lista de dados.")

    # Inicializa os valores do formulário no session_state se não existirem
    if 'quantidade_input_value' not in st.session_state:
        st.session_state['quantidade_input_value'] = 0.00000001
    if 'custo_total_input_value' not in st.session_state:
        st.session_state['custo_total_input_value'] = 0.01
    if 'ptax_input_value' not in st.session_state:
        st.session_state['ptax_input_value'] = 5.00
    if 'data_op_input_value' not in st.session_state:
        st.session_state['data_op_input_value'] = datetime.today().date()
    if 'hora_op_input_value' not in st.session_state:
        st.session_state['hora_op_input_value'] = datetime.now().time()

    with st.form("form_nova_operacao"):
        current_op_type = st.session_state['current_tipo_operacao']

        # Campos do formulário usando as chaves do session_state para seus valores
        quantidade = st.number_input(
            "Quantidade", 
            min_value=0.00000001, 
            format="%.8f", 
            key="quantidade_input_form", # Chave específica para o widget dentro do form
            value=st.session_state['quantidade_input_value']
        )

        valor_label_base = ""
        if is_foreign_wallet:
            valor_label_base = "Custo Total (em USDT)" if current_op_type == "Compra" else "Total da Venda (em USDT)"
        else:
            valor_label_base = "Custo Total (em BRL)" if current_op_type == "Compra" else "Total da Venda (em BRL)"

        custo_total_input = st.number_input(
            valor_label_base, 
            min_value=0.01, 
            format="%.2f", 
            key="custo_total_input_form", # Chave específica para o widget dentro do form
            value=st.session_state['custo_total_input_value']
        )

        ptax_input = 1.0 # Default para carteiras nacionais, ou se não for informada
        valor_em_brl_preview = 0.0

        if is_foreign_wallet:
            ptax_input = st.number_input(
                "Taxa PTAX (BRL por USDT)",
                min_value=0.01,
                format="%.4f",
                key="ptax_input_form", # Chave específica para o widget dentro do form
                value=st.session_state['ptax_input_value']
            )
            valor_em_brl_preview = custo_total_input * ptax_input 
        else:
            valor_em_brl_preview = custo_total_input


        data_operacao = st.date_input(
            "Data da Operação", 
            key="data_op_input_form", # Chave específica para o widget dentro do form
            value=st.session_state['data_op_input_value'],
            min_value=date(2000, 1, 1), # Ano mínimo
            max_value=date(2100, 12, 31), # Ano máximo
            format="DD/MM/YYYY" # Formato de exibição
        )
        hora_operacao = st.time_input(
            "Hora da Operação", 
            key="hora_op_input_form", # Chave específica para o widget dentro do form
            value=st.session_state['hora_op_input_value']
        )

        submitted_op = st.form_submit_button("Registrar Operação ✅")

        if submitted_op:
            # Validação para garantir que uma criptomoeda foi selecionada
            if not selected_crypto_for_display:
                st.error("Por favor, selecione uma criptomoeda.")
            elif quantidade <= 0 or custo_total_input <= 0:
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
                        (df_operacoes_existentes['cripto'] == cripto_symbol) & # Usar o símbolo aqui
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
                    "cripto": str(cripto_symbol), # Salva o símbolo (ex: BTC, SOL, MEUCUSTOM)
                    "cripto_display_name": selected_crypto_for_display['display_name'], # Salva o nome de exibição completo
                    "cripto_image_url": selected_crypto_for_display['image'], # Salva a URL da imagem
                    "quantidade": float(quantidade), # Garante que a quantidade é salva como float
                    "custo_total": custo_total_final_brl, # Salva o valor já convertido para BRL
                    "data_operacao": data_hora_completa,
                    "preco_medio_compra_na_op": preco_medio_compra_na_op,
                    "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                    "ptax_na_op": ptax_input # Salva a PTAX utilizada
                }])

                save_operacoes(pd.concat([df_operacoes_existentes, nova_operacao], ignore_index=True))
                st.success("Operação registrada com sucesso!")
                
                # Limpa os campos do formulário redefinindo os valores no session_state
                st.session_state['quantidade_input_value'] = 0.00000001
                st.session_state['custo_total_input_value'] = 0.01
                st.session_state['ptax_input_value'] = 5.00 
                st.session_state['data_op_input_value'] = datetime.today().date()
                st.session_state['hora_op_input_value'] = datetime.now().time()
                
                # Resetar a seleção de cripto para a primeira opção da lista após o registro
                st.session_state['selected_crypto_display_name'] = display_options[0] if display_options else None
                
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
                # Modificar a exibição da quantidade para usar format_number_br
                op_info_display = (f"{op_details['tipo_operacao']} de {format_number_br(op_details['quantidade'], decimals=8)} "
                                f"{op_details['cripto_display_name']} ({format_currency_brl(op_details['custo_total'])}) em " # Usa cripto_display_name
                                f"{op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}")

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-bottom:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
                    <p>Você tem certeza que deseja excluir a seguinte operação?</p>
                    <p style="font-weight:bold;">{op_info_display}</p>
                    <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível e não poderá ser desfeita.</p>
                    <p>Deseja realmente continuar?</p>
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
        # Usar a lista completa de criptos para o filtro, se disponível
        full_crypto_data_for_filter = cryptocurrencies_data_df
        # Extrair apenas os display_name para o multiselect
        all_cryptos_display_names = full_crypto_data_for_filter['display_name'].tolist()

        # Mapear display_name de volta para symbol para o filtro real
        filter_display_to_symbol_map = {crypto['display_name']: crypto['symbol'] for crypto in full_crypto_data_for_filter.to_dict('records')}

        filter_crypto_display = st.multiselect("Cripto", all_cryptos_display_names, key="filter_op_crypto")
        # Converter os display names selecionados de volta para símbolos para filtrar o DataFrame
        filter_crypto_symbols = [filter_display_to_symbol_map[d_name] for d_name in filter_crypto_display]


    with col_filter3:
        filter_date_range = st.date_input("Data", value=[], key="filter_op_date_range")

    filtered_operations = wallet_operations_all.copy()

    if filter_type:
        filtered_operations = filtered_operations[filtered_operations['tipo_operacao'].isin(filter_type)]
    if filter_crypto_symbols: # Usar os símbolos para filtrar
        filtered_operations = filtered_operations[filtered_operations['cripto'].isin(filter_crypto_symbols)]
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
        # Definindo as colunas e seus respectivos ratios (REVERTIDO para mais básico)
        col_names = [
            "Tipo", "Cripto", "Qtd.", "PTAX",
            "Valor Total (USDT)", "Valor Total (BRL)", "P. Médio Compra",
            "P. Médio Venda", "Lucro/Prejuízo", "Data/Hora", "Origem", "Ações"
        ]
        # Ajustando os ratios das colunas (REVERTIDO)
        cols_ratio = [0.06, 0.12, 0.08, 0.07, 0.10, 0.10, 0.10, 0.10, 0.10, 0.09, 0.08, 0.05] 

        cols = st.columns(cols_ratio)
        for i, col_name in enumerate(col_names):
            with cols[i]:
                st.markdown(f"**{col_name}**")
        st.markdown("---")

        sorted_operations = filtered_operations.sort_values(by='data_operacao', ascending=False)

        for idx, op_row in sorted_operations.iterrows():
            cols = st.columns(cols_ratio)
            with cols[0]:
                # Colorir o tipo de operação
                color_tipo = "green" if op_row['tipo_operacao'] == "Compra" else "red"
                st.markdown(f"<span style='color:{color_tipo}'>{op_row['tipo_operacao']}</span>", unsafe_allow_html=True)
            with cols[1]: # Coluna Cripto (agora usa o display name)
                st.write(op_row['cripto_display_name']) # Exibe o nome de exibição
            with cols[2]:
                # Formatar a quantidade com ponto e vírgula do Brasil
                st.write(format_number_br(op_row['quantidade'], decimals=8)) 
            with cols[3]: # PTAX
                if pd.notna(op_row['ptax_na_op']):
                    # Formatar PTAX com 4 casas decimais
                    st.write(format_number_br(op_row['ptax_na_op'], decimals=4))
                else:
                    st.write("-")
            with cols[4]: # Valor Total (USDT)
                if is_foreign_wallet and pd.notna(op_row['custo_total_usdt']):
                    # Formatar Valor Total (USDT) com 2 casas decimais
                    st.write(f"USDT {format_number_br(op_row['custo_total_usdt'], decimals=2)}") # Linha corrigida
                else:
                    st.write("-")
            with cols[5]: # Valor Total (BRL)
                st.write(format_currency_brl(op_row['custo_total']))
            with cols[6]:
                if op_row['tipo_operacao'] == 'Compra' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(format_currency_brl(op_row['preco_medio_compra_na_op']))
                elif op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(format_currency_brl(op_row['preco_medio_compra_na_op']))
                else:
                    st.write("-")
            with cols[7]:
                if op_row['tipo_operacao'] == 'Venda' and op_row['quantidade'] > 0:
                    st.write(format_currency_brl(op_row["custo_total"] / op_row["quantidade"]))
                else:
                    st.write("-")
            with cols[8]:
                if op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['lucro_prejuizo_na_op']):
                    profit_loss = op_row['lucro_prejuizo_na_op']
                    color = "green" if profit_loss >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>{format_currency_brl(profit_loss)}</span>", unsafe_allow_html=True)
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


# A lógica de persistência de login é a maneira como você inicializa 'logged_in' e 'cpf'
# Se 'logged_in' já é True na sessão (o que acontece em uma atualização se não for resetado explicitamente),
# então o usuário permanece logado.
if st.session_state["logged_in"]:
    show_dashboard()
else:
    show_login()
