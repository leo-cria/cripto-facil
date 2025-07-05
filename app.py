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
    """Gera um hash SHA256 do password fornecida para armazenamento seguro."""
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

        # --- NOVO: Garante que a coluna 'referencia_transacao' exista ---
        if 'referencia_transacao' not in df.columns:
            df['referencia_transacao'] = ""
        else:
            df['referencia_transacao'] = df['referencia_transacao'].astype(str).replace('nan', '')

        return df
    return pd.DataFrame(columns=[
        "id", "wallet_id", "cpf_usuario", "tipo_operacao", "cripto",
        "quantidade", "custo_total", "data_operacao",
        "preco_medio_compra_na_op",
        "lucro_prejuizo_na_op",
        "ptax_na_op",
        "cripto_display_name", # Adicionada nova coluna
        "cripto_image_url", # Adicionada nova coluna
        "referencia_transacao" # Adicionada nova coluna
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

        # Formulário de cadastro de nova carteira dentro de um expander
        with st.expander("➕ Criar nova carteira"):
            # st.markdown("""
            #     <div style='border:2px solid #e0e0e0; border-radius:10px; padding:20px; background-color:#fafafa;'>
            #         <h3 style='margin-top:0;'>Criar nova carteira</h3>
            #     </div>
            # """, unsafe_allow_html=True) # Removei o markdown para usar o título do expander

            tipo_selecionado_criar = st.radio(
                "Tipo de carteira",
                ["Auto Custódia", "Corretora", "Banco"], # Adicionado "Banco"
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
                    pass
                elif tipo_selecionado_criar == "Banco": # NOVO: Campos para tipo "Banco"
                    nome_input_criar = st.selectbox("Banco", ["NUBANK", "ITAU", "MERCADO PAGO"], key="banco_selector_criar")
                    # info1 e info2 podem ser usados para agência/conta se necessário, por enquanto vazios
                    pass

                nacional_input_criar = st.radio("Origem da carteira:", ["Nacional", "Estrangeira"], key="nacionalidade_radio_field_criar")

                enviado_criar = st.form_submit_button("Criar carteira ➕")
                if enviado_criar:
                    if tipo_selecionado_criar == "Auto Custódia" and (not nome_input_criar or not info1_input_criar):
                        st.error("Por favor, preencha todos os campos obrigatórios para Auto Custódia.")
                    elif (tipo_selecionado_criar == "Corretora" or tipo_selecionado_criar == "Banco") and not nome_input_criar:
                        st.error(f"Por favor, selecione uma {tipo_selecionado_criar.lower()}.")
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
                # Adaptação para exibir informações da carteira de forma dinâmica
                display_info = ""
                if row['tipo'] == 'Auto Custódia' and str(row['info1']).strip().lower() != 'nan' and str(row['info1']).strip() != '':
                    display_info = f" - Endereço: {row['info1']}"
                elif row['tipo'] == 'Corretora':
                    display_info = "" # Corretores já tem o nome como principal
                elif row['tipo'] == 'Banco':
                    display_info = "" # Bancos já tem o nome como principal
                
                with st.expander(f"🔗 {row['nome']} ({row['tipo']}){display_info} - Origem: {row['nacional']}", expanded=False):
                    st.write(f"**Tipo:** {row['tipo']}")
                    st.write(f"**Origem:** {row['nacional']}")

                    if row['tipo'] == 'Auto Custódia' and str(row['info1']).strip().lower() != 'nan' and str(row['info1']).strip() != '':
                        st.write(f"**Endereço da Carteira:** {row['info1']}")
                    elif row['tipo'] == 'Corretora':
                        if str(row['info1']).strip().lower() != 'nan' and str(row['info1']).strip() != '':
                            st.write(f"**API Key (Antiga):** {row['info1']}")
                        if str(row['info2']).strip().lower() != 'nan' and str(row['info2']).strip() != '':
                            st.write(f"**Secret Key (Antiga):** {row['info2']}")
                    # Para 'Banco', não há info1/info2 específicas para exibir por padrão

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
    # Para o tipo "Banco", não há info1/info2 a serem exibidas por padrão aqui.

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

            # Considera "Recebimento" como aumento e "Envio" como diminuição da quantidade
            qtd_comprada_ou_recebida = ops_cripto[
                (ops_cripto['tipo_operacao'] == 'Compra') | 
                (ops_cripto['tipo_operacao'] == 'Recebimento')
            ]['quantidade'].sum()
            
            qtd_vendida_ou_enviada = ops_cripto[
                (ops_cripto['tipo_operacao'] == 'Venda') | 
                (ops_cripto['tipo_operacao'] == 'Envio')
            ]['quantidade'].sum()
            
            quantidade_atual = qtd_comprada_ou_recebida - qtd_vendida_ou_enviada

            if quantidade_atual > 0:
                # O custo total e custo base vendido ainda são apenas de Compra/Venda
                total_custo_comprado = ops_cripto[ops_cripto['tipo_operacao'] == 'Compra']['custo_total'].sum()
                total_custo_base_vendido = 0
                vendas_da_cripto = ops_cripto[ops_cripto['tipo_operacao'] == 'Venda']
                if not vendas_da_cripto.empty:
                    total_custo_base_vendido = (vendas_da_cripto['quantidade'] * vendas_da_cripto['preco_medio_compra_na_op']).sum()

                custo_total_atual_estimado = total_custo_comprado - total_custo_base_vendido
                
                if quantidade_atual > 0:
                    custo_medio = custo_total_atual_estimado / quantidade_atual
                else:
                    custo_medio = 0

                lucro_realizado_cripto = ops_cripto[
                    (ops_cripto['tipo_operacao'] == 'Venda') & 
                    (pd.notna(ops_cripto['lucro_prejuizo_na_op']))
                ]['lucro_prejuizo_na_op'].sum()

                current_price = crypto_prices.get(cripto_simbolo.upper(), 0.0)
                valor_atual_posicao = quantidade_atual * current_price
                total_valor_atual_carteira += valor_atual_posicao

                last_op_for_crypto = ops_cripto.sort_values(by='data_operacao', ascending=False).iloc[0]
                display_name_for_portfolio = last_op_for_crypto['cripto_display_name']
                image_url_for_portfolio = last_op_for_crypto['cripto_image_url']

                portfolio_detail[cripto_simbolo] = {
                    'display_name': display_name_for_portfolio,
                    'image': image_url_for_portfolio,
                    'quantidade': float(quantidade_atual),
                    'custo_total': float(custo_total_atual_estimado),
                    'custo_medio': float(custo_medio),
                    'lucro_realizado': float(lucro_realizado_cripto),
                    'current_price_brl': float(current_price),
                    'valor_atual_posicao': float(valor_atual_posicao)
                }
    
    portfolio_df = pd.DataFrame.from_dict(portfolio_detail, orient='index')
    if not portfolio_df.empty:
        portfolio_df = portfolio_df.reset_index().rename(columns={
            'index': 'Cripto_Symbol',
            'display_name': 'Cripto',
            'image': 'Logo',
            'quantidade': 'Quantidade',
            'custo_total': 'Custo Total',
            'custo_medio': 'Custo Médio',
            'lucro_realizado': 'Lucro Realizado',
            'current_price_brl': 'Preço Atual (BRL)',
            'valor_atual_posicao': 'Valor Atual da Posição'
        })
        portfolio_df = portfolio_df[portfolio_df['Quantidade'] > 0]
        total_custo_carteira_atualizado = portfolio_df['Custo Total'].sum()
    else:
        total_custo_carteira_atualizado = 0.0

    col_custo, col_lucro, col_valor_atual = st.columns(3)
    with col_custo:
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Custo Total da Carteira (Ativo) (BRL)</p>"
            f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_custo_carteira_atualizado)}</p>", unsafe_allow_html=True
        )
    with col_lucro:
        color_lucro_total = "green" if total_lucro_realizado > 0 else ("red" if total_lucro_realizado < 0 else "black")
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Lucro Realizado Total da Carteira (BRL)</p>"
            f"<p style='text-align: center; color: {color_lucro_total}; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_lucro_realizado)}</p>", unsafe_allow_html=True
        )
    with col_valor_atual:
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Valor Atual da Carteira (BRL)</p>"
            f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_valor_atual_carteira)}</p>", unsafe_allow_html=True
        )
    
    if last_updated_timestamp:
        try:
            updated_dt = datetime.fromisoformat(last_updated_timestamp)
            st.markdown(f"<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Última atualização de preços: {updated_dt.strftime('%d/%m/%Y %H:%M:%S')}</p>", unsafe_allow_html=True)
        except ValueError:
            st.markdown("<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Data de atualização de preços não disponível.</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align: center; font-size: 14px; margin-top: 5px;'>Data de atualização de preços não disponível.</p>", unsafe_allow_html=True)


    if not portfolio_df.empty:
        st.markdown("##### Detalhes do Portfólio por Cripto")
        # Colunas a serem exibidas na tabela
        display_columns = [
            'Logo', 'Cripto', 'Quantidade', 'Custo Médio', 'Custo Total', 
            'Preço Atual (BRL)', 'Valor Atual da Posição', 'Lucro Realizado'
        ]

        # Formatação para exibição na tabela
        portfolio_display_df = portfolio_df[display_columns].copy()
        portfolio_display_df['Quantidade'] = portfolio_display_df['Quantidade'].apply(lambda x: format_number_br(x, 8)) # Mais precisão
        portfolio_display_df['Custo Médio'] = portfolio_display_df['Custo Médio'].apply(format_currency_brl)
        portfolio_display_df['Custo Total'] = portfolio_display_df['Custo Total'].apply(format_currency_brl)
        portfolio_display_df['Preço Atual (BRL)'] = portfolio_display_df['Preço Atual (BRL)'].apply(format_currency_brl)
        portfolio_display_df['Valor Atual da Posição'] = portfolio_display_df['Valor Atual da Posição'].apply(format_currency_brl)
        portfolio_display_df['Lucro Realizado'] = portfolio_display_df['Lucro Realizado'].apply(format_currency_brl)

        # Para exibir imagens na coluna 'Logo'
        st.dataframe(
            portfolio_display_df,
            column_config={
                "Logo": st.column_config.ImageColumn("Logo", help="Logo da Criptomoeda", width="small"),
                "Cripto": st.column_config.Column("Criptomoeda", width="medium"),
                "Quantidade": st.column_config.Column("Quantidade", width="small"),
                "Custo Médio": st.column_config.Column("Custo Médio", width="small"),
                "Custo Total": st.column_config.Column("Custo Total", width="small"),
                "Preço Atual (BRL)": st.column_config.Column("Preço Atual (BRL)", width="small"),
                "Valor Atual da Posição": st.column_config.Column("Valor Atual da Posição", width="small"),
                "Lucro Realizado": st.column_config.Column("Lucro Realizado", width="small")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhuma criptomoeda no portfólio desta carteira ainda.")

    st.markdown("---")

    # --- Registro de Nova Operação ---
    st.markdown("#### Registrar Nova Operação")
    with st.expander("➕ Nova Operação"):
        with st.form("form_add_operacao"):
            tipo_operacao = st.radio(
                "Tipo de Operação",
                ["Compra", "Venda", "Envio", "Recebimento"], # Adicionado 'Envio' e 'Recebimento'
                key="tipo_op_radio_detail",
                horizontal=True
            )

            # Carrega a lista de criptomoedas disponíveis para seleção
            cryptos_for_select = [""] + sorted(cryptocurrencies_data_df['display_name'].tolist())
            selected_crypto_display_name = st.selectbox(
                "Selecione a Criptomoeda",
                cryptos_for_select,
                key="select_crypto_op"
            )
            
            # Pega o símbolo da cripto selecionada
            selected_crypto_symbol = ""
            selected_crypto_image_url = "🪙" # Default emoji
            if selected_crypto_display_name:
                crypto_row = cryptocurrencies_data_df[cryptocurrencies_data_df['display_name'] == selected_crypto_display_name]
                if not crypto_row.empty:
                    selected_crypto_symbol = crypto_row['symbol'].iloc[0]
                    selected_crypto_image_url = crypto_row['image'].iloc[0]

            quantidade_op = st.number_input(
                "Quantidade",
                min_value=0.00000001, # Mínimo para quantidades
                format="%.8f", # Mais casas decimais para criptos
                key="quantidade_op"
            )

            custo_total_op = 0.0 # Inicializa como 0.0

            if tipo_operacao in ["Compra", "Venda"]:
                custo_total_op = st.number_input(
                    "Custo Total (BRL)",
                    min_value=0.01,
                    format="%.2f",
                    key="custo_total_op"
                )
            
            # Novo campo para referência da transação (opcional para Envio/Recebimento)
            referencia_transacao_op = ""
            if tipo_operacao in ["Envio", "Recebimento"]:
                referencia_transacao_op = st.text_input(
                    "Referência da Transação (Opcional)",
                    help="Ex: ID da transação na blockchain, hash, etc.",
                    key="referencia_transacao_op"
                )

            data_operacao_op = st.date_input(
                "Data da Operação",
                value="today",
                key="data_op"
            )

            submit_op = st.form_submit_button("Registrar Operação")

            if submit_op:
                if not selected_crypto_display_name:
                    st.error("Por favor, selecione uma criptomoeda.")
                elif quantidade_op <= 0:
                    st.error("A quantidade deve ser maior que zero.")
                elif tipo_operacao in ["Compra", "Venda"] and custo_total_op <= 0:
                    st.error("O custo total deve ser maior que zero para operações de Compra ou Venda.")
                else:
                    df_operacoes = load_operacoes()
                    
                    preco_medio_compra_na_op = None
                    lucro_prejuizo_na_op = None

                    if tipo_operacao == "Compra":
                        # Calcule o preço médio de compra (não o acumulado, mas o desta operação)
                        preco_medio_compra_na_op = custo_total_op / quantidade_op
                    elif tipo_operacao == "Venda":
                        # Para Venda, precisamos calcular o lucro/prejuízo
                        # 1. Obter o custo médio ponderado da cripto nesta carteira antes da venda
                        ops_anteriores = df_operacoes[
                            (df_operacoes['wallet_id'] == wallet_id) &
                            (df_operacoes['cpf_usuario'] == user_cpf) &
                            (df_operacoes['cripto'] == selected_crypto_symbol) &
                            ((df_operacoes['tipo_operacao'] == 'Compra') | (df_operacoes['tipo_operacao'] == 'Recebimento'))
                        ].copy()

                        qtd_acumulada = ops_anteriores[
                            (ops_anteriores['tipo_operacao'] == 'Compra') | 
                            (ops_anteriores['tipo_operacao'] == 'Recebimento')
                        ]['quantidade'].sum()
                        
                        custo_total_acumulado = ops_anteriores[ops_anteriores['tipo_operacao'] == 'Compra']['custo_total'].sum()

                        # Subtrair quantidades de vendas e envios anteriores para ter o saldo real
                        qtd_vendas_anteriores = df_operacoes[
                            (df_operacoes['wallet_id'] == wallet_id) &
                            (df_operacoes['cpf_usuario'] == user_cpf) &
                            (df_operacoes['cripto'] == selected_crypto_symbol) &
                            ((df_operacoes['tipo_operacao'] == 'Venda') | (df_operacoes['tipo_operacao'] == 'Envio'))
                        ]['quantidade'].sum()

                        saldo_atual_antes_venda = qtd_acumulada - qtd_vendas_anteriores

                        if quantidade_op > saldo_atual_antes_venda:
                            st.error(f"Quantidade de venda ({format_number_br(quantidade_op, 8)}) excede o saldo disponível ({format_number_br(saldo_atual_antes_venda, 8)}) de {selected_crypto_display_name}.")
                            st.stop() # Interrompe a execução
                        
                        custo_medio_ponderado_anterior = 0.0
                        if qtd_acumulada > 0: # Não pode dividir por zero
                            # Recalcular custo_total_ativo
                            # O custo_total_ativo precisa subtrair o custo-base das vendas anteriores
                            
                            # Soma o custo_total de todas as Compras
                            total_comprado_historico = df_operacoes[
                                (df_operacoes['wallet_id'] == wallet_id) &
                                (df_operacoes['cpf_usuario'] == user_cpf) &
                                (df_operacoes['cripto'] == selected_crypto_symbol) &
                                (df_operacoes['tipo_operacao'] == 'Compra')
                            ]['custo_total'].sum() or 0.0

                            # Soma a quantidade de todas as Compras e Recebimentos
                            total_qtd_comprada_recebida_historico = df_operacoes[
                                (df_operacoes['wallet_id'] == wallet_id) &
                                (df_operacoes['cpf_usuario'] == user_cpf) &
                                (df_operacoes['cripto'] == selected_crypto_symbol) &
                                ((df_operacoes['tipo_operacao'] == 'Compra') | (df_operacoes['tipo_operacao'] == 'Recebimento'))
                            ]['quantidade'].sum() or 0.0

                            # Soma a quantidade de todas as Vendas e Envios (para determinar o saldo atual para o cálculo do custo médio)
                            total_qtd_vendida_enviada_historico = df_operacoes[
                                (df_operacoes['wallet_id'] == wallet_id) &
                                (df_operacoes['cpf_usuario'] == user_cpf) &
                                (df_operacoes['cripto'] == selected_crypto_symbol) &
                                ((df_operacoes['tipo_operacao'] == 'Venda') | (df_operacoes['tipo_operacao'] == 'Envio'))
                            ]['quantidade'].sum() or 0.0
                            
                            saldo_qtd_ativo_para_custo = total_qtd_comprada_recebida_historico - total_qtd_vendida_enviada_historico
                            
                            # Agora, para o custo base das unidades *ainda em carteira*, 
                            # precisamos de um cálculo mais sofisticado (FIFO, LIFO, Custo Médio).
                            # Para simplificar, vamos assumir Custo Médio Ponderado para o cálculo do lucro.
                            # Para a venda, o preco_medio_compra_na_op será o custo médio ponderado atual.

                            if saldo_qtd_ativo_para_custo > 0:
                                custo_total_para_calculo_medio = total_comprado_historico
                                
                                # Subtrair o custo base das vendas *anteriores* para ter o custo base das unidades remanescentes
                                # Este é um ponto complexo; a maneira mais simples para um MVP é ignorar FIFO/LIFO
                                # e assumir que cada venda usa o "custo médio" da época da venda para o cálculo do lucro,
                                # e o custo médio ponderado geral é para o ativo remanescente.
                                
                                # Para o cálculo da VENDA, precisamos do custo médio PONDERADO ATUAL.
                                # O custo_medio_ponderado_anterior é o custo das unidades que *ainda estão* na carteira.
                                
                                # Filtrar apenas as compras para calcular o custo médio ponderado para fins de venda
                                apenas_compras = df_operacoes[
                                    (df_operacoes['wallet_id'] == wallet_id) &
                                    (df_operacoes['cpf_usuario'] == user_cpf) &
                                    (df_operacoes['cripto'] == selected_crypto_symbol) &
                                    (df_operacoes['tipo_operacao'] == 'Compra')
                                ]
                                
                                # Soma das quantidades e custos das compras
                                total_comprado_qtd = apenas_compras['quantidade'].sum() or 0.0
                                total_comprado_custo = apenas_compras['custo_total'].sum() or 0.0

                                if total_comprado_qtd > 0:
                                    custo_medio_ponderado_anterior = total_comprado_custo / total_comprado_qtd
                                else:
                                    custo_medio_ponderado_anterior = 0.0

                                # Se houver vendas anteriores, estas já teriam "realizado" parte do custo.
                                # Isso é para simplificar: a venda atual usa o custo médio ponderado de *todas as compras* até agora,
                                # desconsiderando complexidades de FIFO/LIFO entre vendas.
                                # Para um sistema financeiro real, o ideal seria implementar FIFO/LIFO.
                                
                                preco_medio_compra_na_op = custo_medio_ponderado_anterior
                                lucro_prejuizo_na_op = (custo_total_op - (quantidade_op * preco_medio_compra_na_op))
                            else:
                                st.warning("Não há quantidade suficiente da criptomoeda para realizar a venda com custo médio calculado.")
                                preco_medio_compra_na_op = 0.0
                                lucro_prejuizo_na_op = custo_total_op # Lucro total se não houver custo base. Isso é um caso de erro ou doação.

                    # Para Envio e Recebimento, custo_total_op é 0, e preco_medio_compra_na_op e lucro_prejuizo_na_op são None/NaN
                    if tipo_operacao in ["Envio", "Recebimento"]:
                        custo_total_op = 0.0
                        preco_medio_compra_na_op = float('nan') # Usar NaN para indicar não aplicável
                        lucro_prejuizo_na_op = float('nan') # Usar NaN para indicar não aplicável

                    nova_operacao = pd.DataFrame([{
                        "id": f"operacao_{uuid.uuid4()}",
                        "wallet_id": wallet_id,
                        "cpf_usuario": user_cpf,
                        "tipo_operacao": tipo_operacao,
                        "cripto": selected_crypto_symbol,
                        "quantidade": quantidade_op,
                        "custo_total": custo_total_op,
                        "data_operacao": pd.to_datetime(data_operacao_op),
                        "preco_medio_compra_na_op": preco_medio_compra_na_op,
                        "lucro_prejuizo_na_op": lucro_prejuizo_na_op,
                        "ptax_na_op": float('nan'), # Pode ser preenchido se for uma operação em real e a carteira estrangeira
                        "cripto_display_name": selected_crypto_display_name,
                        "cripto_image_url": selected_crypto_image_url,
                        "referencia_transacao": referencia_transacao_op # Salva a referência da transação
                    }])
                    
                    save_operacoes(pd.concat([df_operacoes, nova_operacao], ignore_index=True))
                    st.success(f"Operação de {tipo_operacao} registrada com sucesso para {selected_crypto_display_name}!")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Histórico de Operações")
    df_operacoes_current = load_operacoes()
    wallet_ops = df_operacoes_current[
        (df_operacoes_current['wallet_id'] == wallet_id) &
        (df_operacoes_current['cpf_usuario'] == user_cpf)
    ].sort_values(by='data_operacao', ascending=False).reset_index(drop=True)

    if not wallet_ops.empty:
        # Crie uma cópia para formatação e exibição
        wallet_ops_display = wallet_ops.copy()

        # Formatar colunas para exibição
        wallet_ops_display['data_operacao'] = wallet_ops_display['data_operacao'].dt.strftime('%d/%m/%Y %H:%M')
        wallet_ops_display['quantidade'] = wallet_ops_display['quantidade'].apply(lambda x: format_number_br(x, 8))
        wallet_ops_display['custo_total'] = wallet_ops_display['custo_total'].apply(format_currency_brl)
        wallet_ops_display['preco_medio_compra_na_op'] = wallet_ops_display['preco_medio_compra_na_op'].apply(lambda x: format_currency_brl(x) if pd.notna(x) else '-')
        
        # Formata lucro/prejuízo com cor
        def format_lucro_prejuizo(value):
            if pd.isna(value):
                return '-'
            color = "green" if value > 0 else ("red" if value < 0 else "black")
            return f"<span style='color:{color}; font-weight:bold;'>{format_currency_brl(value)}</span>"

        wallet_ops_display['lucro_prejuizo_na_op'] = wallet_ops_display['lucro_prejuizo_na_op'].apply(format_lucro_prejuizo)
        
        # Display name e image url
        wallet_ops_display['Cripto'] = wallet_ops_display['cripto_display_name']
        wallet_ops_display['Logo'] = wallet_ops_display['cripto_image_url']

        # Renomear e selecionar colunas para exibição
        display_columns = [
            'Logo', 'Cripto', 'tipo_operacao', 'quantidade', 'custo_total', 
            'preco_medio_compra_na_op', 'lucro_prejuizo_na_op', 'data_operacao',
            'referencia_transacao', # Adicionada a coluna de referência
            'id' # Manter o ID para o botão de exclusão
        ]
        
        wallet_ops_display = wallet_ops_display[display_columns].rename(columns={
            'tipo_operacao': 'Tipo',
            'quantidade': 'Quantidade',
            'custo_total': 'Custo/Valor',
            'data_operacao': 'Data',
            'preco_medio_compra_na_op': 'Preço Médio (CPA)', # Renomeado para CPA
            'lucro_prejuizo_na_op': 'Lucro/Prejuízo Realizado',
            'referencia_transacao': 'Referência da Transação'
        })
        
        # Adicionar coluna de exclusão
        wallet_ops_display['Ação'] = [f"🗑️ Excluir_{idx}" for idx in wallet_ops_display['id']]

        st.dataframe(
            wallet_ops_display,
            column_config={
                "Logo": st.column_config.ImageColumn("Logo", help="Logo da Criptomoeda", width="small"),
                "Cripto": st.column_config.Column("Criptomoeda", width="medium"),
                "Tipo": st.column_config.Column("Tipo", width="small"),
                "Quantidade": st.column_config.Column("Quantidade", width="small"),
                "Custo/Valor": st.column_config.Column("Custo/Valor (BRL)", width="small"),
                "Preço Médio (CPA)": st.column_config.Column("Preço Médio de Compra Adquirido (BRL)", width="small"),
                "Lucro/Prejuízo Realizado": st.column_config.Column("Lucro/Prejuízo Realizado (BRL)", width="small", help="Lucro ou Prejuízo apurado na Venda"),
                "Data": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY HH:mm", width="small"),
                "Referência da Transação": st.column_config.Column("Referência da Transação", width="medium", help="ID ou hash da transação"),
                "id": None, # Esconde a coluna ID original
                "Ação": st.column_config.ButtonColumn("Ação", help="Clique para excluir a operação", width="small")
            },
            hide_index=True,
            use_container_width=True
        )

        clicked_button = st.experimental_get_query_params().get("Ação")
        if clicked_button:
            operation_id_to_delete = clicked_button[0].replace("🗑️ Excluir_", "")
            st.session_state['confirm_delete_operation_id'] = operation_id_to_delete
            st.experimental_set_query_params() # Limpa o query param para evitar re-execução
            st.rerun()

    else:
        st.info("Nenhuma operação registrada para esta carteira ainda.")

    # Modal de confirmação de exclusão de operação
    operation_confirm_placeholder = st.empty()
    if st.session_state.get('confirm_delete_operation_id'):
        with operation_confirm_placeholder.container():
            op_to_confirm_delete_id = st.session_state['confirm_delete_operation_id']
            op_details = wallet_ops[wallet_ops['id'] == op_to_confirm_delete_id].iloc[0]
            op_display = f"{op_details['tipo_operacao']} de {op_details['quantidade']} {op_details['cripto_display_name']} em {op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}"

            st.markdown(f"""
            <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-top:20px;">
                <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
                <p>Você tem certeza que deseja excluir a seguinte operação?</p>
                <p><strong>{op_display}</strong></p>
                <p style="color:#ff0000; font-weight:bold;">Esta ação é irreversível!</p>
                <p>Deseja realmente continuar?</p>
            </div>
            """, unsafe_allow_html=True)

            col_confirm_op, col_cancel_op = st.columns([0.2, 0.8])
            with col_confirm_op:
                if st.button("Sim, Excluir", key="confirm_op_delete_btn_modal"):
                    df_operacoes_updated = df_operacoes_current[df_operacoes_current['id'] != op_to_confirm_delete_id]
                    save_operacoes(df_operacoes_updated)
                    st.success(f"Operação excluída com sucesso!")
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

# --- Funções de Autenticação e Fluxo Principal ---
def login_page():
    """Exibe a página de login."""
    st.title("Bem-vindo(a) ao Cripto Fácil!")
    st.subheader("Acesse sua conta")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        login_button = st.form_submit_button("Entrar")

        if login_button:
            df_users = load_users()
            user = df_users[(df_users['email'] == email) & (df_users['password_hash'] == hash_password(password))]
            if not user.empty:
                st.session_state["logged_in"] = True
                st.session_state["cpf"] = user['cpf'].iloc[0]
                st.session_state["username"] = user['name'].iloc[0]
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
    
    st.markdown("---")
    st.markdown("Não tem conta? [Crie uma agora](#cadastro)")
    st.markdown("Esqueceu sua senha? [Recupere aqui](#esqueci-senha)")
    
    st.markdown("<h2 id='cadastro'>Criar nova conta</h2>", unsafe_allow_html=True)
    with st.form("register_form"):
        st.subheader("Crie sua conta")
        new_name = st.text_input("Nome Completo", key="reg_name")
        new_cpf = st.text_input("CPF (somente números)", max_chars=11, help="Ex: 12345678900", key="reg_cpf")
        new_phone = st.text_input("Telefone", help="Ex: 5511998765432", key="reg_phone")
        new_email = st.text_input("Email", key="reg_email")
        new_password = st.text_input("Senha", type="password", key="reg_password")
        confirm_password = st.text_input("Confirme a Senha", type="password", key="reg_confirm_password")
        
        register_button = st.form_submit_button("Registrar")

        if register_button:
            df_users = load_users()
            if not re.fullmatch(r'\d{11}', new_cpf):
                st.error("CPF deve conter exatamente 11 dígitos numéricos.")
            elif new_email and not re.fullmatch(r'[^@]+@[^@]+\.[^@]+', new_email):
                st.error("Formato de email inválido.")
            elif new_cpf in df_users['cpf'].values:
                st.error("CPF já cadastrado.")
            elif new_email in df_users['email'].values:
                st.error("Email já cadastrado.")
            elif new_password != confirm_password:
                st.error("As senhas não conferem.")
            elif len(new_password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                new_user = pd.DataFrame([{
                    "cpf": new_cpf,
                    "name": new_name,
                    "phone": new_phone,
                    "email": new_email,
                    "password_hash": hash_password(new_password)
                }])
                save_users(pd.concat([df_users, new_user], ignore_index=True))
                st.success("Conta criada com sucesso! Faça login para continuar.")
                st.session_state["auth_page"] = "login"
                st.rerun()

def forgot_password_page():
    """Exibe a página de recuperação de senha."""
    st.title("Recuperar Senha")

    if "recovery_step" not in st.session_state:
        st.session_state["recovery_step"] = "request_email"

    if st.session_state["recovery_step"] == "request_email":
        st.subheader("Etapa 1: Informe seu Email")
        with st.form("forgot_password_email_form"):
            email_forgot = st.text_input("Email cadastrado")
            submit_email = st.form_submit_button("Enviar Código de Recuperação")
            if submit_email:
                df_users = load_users()
                user_exists = not df_users[df_users['email'] == email_forgot].empty
                if user_exists:
                    send_recovery_code(email_forgot)
                    st.session_state["recovery_step"] = "verify_code"
                    st.rerun()
                else:
                    st.error("Email não encontrado.")
    
    elif st.session_state["recovery_step"] == "verify_code":
        st.subheader("Etapa 2: Verifique o Código")
        st.info(f"Um código de 6 dígitos foi enviado para {st.session_state.get('reset_email', 'seu email')}. Verifique sua caixa de entrada (e spam).")
        with st.form("verify_code_form"):
            input_code = st.text_input("Digite o código de 6 dígitos", max_chars=6)
            submit_code = st.form_submit_button("Verificar Código")
            if submit_code:
                if input_code == st.session_state.get("recovery_code"):
                    st.session_state["recovery_step"] = "reset_password"
                    st.success("Código verificado com sucesso!")
                    st.rerun()
                else:
                    st.error("Código incorreto.")
        if st.button("Voltar", key="btn_voltar_verify"):
            st.session_state["recovery_step"] = "request_email"
            st.rerun()


    elif st.session_state["recovery_step"] == "reset_password":
        st.subheader("Etapa 3: Redefinir sua Senha")
        with st.form("reset_password_form"):
            new_pass = st.text_input("Nova Senha", type="password")
            confirm_new_pass = st.text_input("Confirme a Nova Senha", type="password")
            reset_button = st.form_submit_button("Redefinir Senha")
            if reset_button:
                if new_pass != confirm_new_pass:
                    st.error("As senhas não conferem.")
                elif len(new_pass) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres.")
                else:
                    df_users = load_users()
                    email_to_reset = st.session_state.get("reset_email")
                    df_users.loc[df_users['email'] == email_to_reset, 'password_hash'] = hash_password(new_pass)
                    save_users(df_users)
                    st.success("Senha redefinida com sucesso! Você já pode fazer login.")
                    # Limpar estados de recuperação e voltar para o login
                    st.session_state.pop("recovery_step", None)
                    st.session_state.pop("recovery_code", None)
                    st.session_state.pop("reset_email", None)
                    st.session_state["auth_page"] = "login"
                    st.rerun()
        if st.button("Voltar", key="btn_voltar_reset"):
            st.session_state["recovery_step"] = "verify_code"
            st.rerun()
    
    st.markdown("---")
    if st.button("Voltar para o Login", key="btn_voltar_esqueci"):
        st.session_state["auth_page"] = "login"
        st.session_state.pop("recovery_step", None)
        st.session_state.pop("recovery_code", None)
        st.session_state.pop("reset_email", None)
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

if st.session_state["logged_in"]:
    show_dashboard()
else:
    if st.session_state["auth_page"] == "login":
        login_page()
    elif st.session_state["auth_page"] == "forgot_password":
        forgot_password_page()
        
