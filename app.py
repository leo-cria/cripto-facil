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
                    df_cryptos['current_price_brl'] = pd.to_numeric(df_cryptos['current_price_brl'], errors='coerce')
                
                # Retorna a data de atualização e o DataFrame de criptos
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
        # Pega o primeiro preço encontrado para o símbolo
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
                st.rerun()

        st.markdown("---")
        if st.button("� Sair"):
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
    
    # Carrega os dados de criptomoedas para ter os preços atuais
    last_updated_timestamp, cryptocurrencies_data_df = load_cryptocurrencies_from_file()
    crypto_prices = {crypto['symbol'].upper(): crypto.get('current_price_brl', 0) for crypto in cryptocurrencies_data_df.to_dict('records')}

    # Título do Portfólio Consolidado com a data de atualização
    col_portfolio_title, col_update_date = st.columns([0.7, 0.3])
    with col_portfolio_title:
        st.markdown("#### Portfólio Consolidado da Carteira")
    with col_update_date:
        if last_updated_timestamp:
            try:
                # Converte a string ISO para objeto datetime e formata para dd/mm/aaaa
                updated_dt = datetime.fromisoformat(last_updated_timestamp)
                st.markdown(f"**Atualizado em:** {updated_dt.strftime('%d/%m/%Y')}")
            except ValueError:
                st.markdown("Não foi possível formatar a data de atualização da API.")
        else:
            st.markdown("Data de atualização da API não disponível.")


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
                current_price = crypto_prices.get(cripto_simbolo.upper(), 0)
                valor_atual_posicao = quantidade_atual * current_price
                total_valor_atual_carteira += valor_atual_posicao # Adiciona ao total da carteira

                # Encontrar a imagem da cripto
                crypto_info = cryptocurrencies_data_df[cryptocurrencies_data_df['symbol'] == cripto_simbolo.upper()]
                image_url = crypto_info['image'].iloc[0] if not crypto_info.empty else ""

                portfolio_detail[cripto_simbolo] = {
                    'image': image_url, # Adiciona a URL da imagem
                    'quantidade': float(quantidade_atual),
                    'custo_total': float(custo_total_atual_estimado),
                    'custo_medio': float(custo_medio),
                    'lucro_realizado': float(lucro_realizado_cripto),
                    'current_price_brl': float(current_price),
                    'valor_atual_posicao': float(valor_atual_posicao)
                }

    # Criar DataFrame para o portfólio detalhado
    portfolio_df = pd.DataFrame.from_dict(portfolio_detail, orient='index').reset_index()
    if not portfolio_df.empty:
        portfolio_df.columns = ['Cripto', 'Imagem', 'Quantidade', 'Custo Total', 'Custo Médio', 'Lucro Realizado', 'Preço Atual (BRL)', 'Valor Atual da Posição']
        portfolio_df = portfolio_df[portfolio_df['Quantidade'] > 0] # Filtrar só as que tem saldo > 0

        # Calcular o Custo Total da Carteira com base no portfolio_df filtrado
        total_custo_carteira_atualizado = portfolio_df['Custo Total'].sum()
    else:
        total_custo_carteira_atualizado = 0.0

    # Exibir as métricas em texto
    col_custo, col_lucro, col_valor_atual = st.columns(3)
    with col_custo:
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Custo Total da Carteira (Ativo)</p>"
            f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_custo_carteira_atualizado)}</p>",
            unsafe_allow_html=True
        )
    with col_lucro:
        # Aplicar cor ao Lucro Realizado Total da Carteira
        color_lucro_total = "green" if total_lucro_realizado > 0 else ("red" if total_lucro_realizado < 0 else "black")
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Lucro Realizado Total da Carteira</p>"
            f"<p style='text-align: center; color: {color_lucro_total}; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_lucro_realizado)}</p>", 
            unsafe_allow_html=True
        )
    with col_valor_atual:
        st.markdown(
            f"<p style='text-align: center; font-size: 18px; margin-bottom: 0;'>Valor Atual da Carteira</p>"
            f"<p style='text-align: center; font-size: 24px; font-weight: bold;'>{format_currency_brl(total_valor_atual_carteira)}</p>",
            unsafe_allow_html=True
        )


    st.markdown("---")
    st.markdown("#### Portfolio Atual Detalhado")
    if not portfolio_df.empty:
        # Calcular a coluna POSIÇÃO
        if total_valor_atual_carteira > 0:
            portfolio_df['POSIÇÃO'] = (portfolio_df['Valor Atual da Posição'] / total_valor_atual_carteira) * 100
        else:
            portfolio_df['POSIÇÃO'] = 0.0

        # Ordenar por 'Custo Total' em ordem decrescente
        portfolio_df = portfolio_df.sort_values(by='Custo Total', ascending=False)

        # Definindo as colunas e seus respectivos ratios (ajustados para a nova coluna "Imagem" e "POSIÇÃO")
        col_names_portfolio = ["Imagem", "Cripto", "Quantidade", "Custo Total", "Custo Médio", "Lucro Realizado", "Preço Atual (BRL)", "Valor Atual da Posição", "POSIÇÃO"]
        cols_ratio_portfolio = [0.05, 0.10, 0.13, 0.13, 0.13, 0.13, 0.13, 0.13, 0.07] # Ajustado para 9 colunas

        cols_portfolio = st.columns(cols_ratio_portfolio)
        for i, col_name in enumerate(col_names_portfolio):
            with cols_portfolio[i]:
                st.markdown(f"**{col_name}**")
        st.markdown("---")

        for idx, row in portfolio_df.iterrows():
            cols_portfolio = st.columns(cols_ratio_portfolio)
            with cols_portfolio[0]: # Coluna Imagem
                if row['Imagem']:
                    st.markdown(f"<img src='{row['Imagem']}' width='24' height='24'>", unsafe_allow_html=True)
                else:
                    st.write("➖")
            with cols_portfolio[1]: # Coluna Cripto
                st.write(row['Cripto'])
            with cols_portfolio[2]:
                # Formatar a quantidade com ponto e vírgula do Brasil
                st.write(format_number_br(row['Quantidade'], decimals=8))
            with cols_portfolio[3]:
                st.write(format_currency_brl(row['Custo Total']))
            with cols_portfolio[4]:
                st.write(format_currency_brl(row['Custo Médio']))
            with cols_portfolio[5]:
                color = "green" if row['Lucro Realizado'] >= 0 else "red"
                st.markdown(f"<span style='color:{color}'>{format_currency_brl(row['Lucro Realizado'])}</span>", unsafe_allow_html=True)
            with cols_portfolio[6]: # Preço Atual (BRL)
                st.write(format_currency_brl(row['Preço Atual (BRL)']))
            with cols_portfolio[7]: # Valor Atual da Posição
                st.write(format_currency_brl(row['Valor Atual da Posição']))
            with cols_portfolio[8]: # POSIÇÃO
                st.write(f"{format_number_br(row['POSIÇÃO'], decimals=2)}%")
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

    # Carrega a lista de dicionários de criptomoedas
    # A variável cryptocurrencies_data_df já é um DataFrame aqui
    # A função load_cryptocurrencies_from_file retorna (last_updated, df_cryptos)
    # Então, cryptocurrencies_data_df é o df_cryptos
    _, cryptocurrencies_data_df = load_cryptocurrencies_from_file()
    
    # Cria uma lista de strings para exibição no selectbox (apenas o display_name)
    display_options = cryptocurrencies_data_df['display_name'].tolist()
    
    # Mapeia o display_name para o objeto completo da criptomoeda para fácil recuperação
    # Convertendo o DataFrame para lista de dicionários para o map
    display_name_to_crypto_map = {crypto['display_name']: crypto for crypto in cryptocurrencies_data_df.to_dict('records')}

    # Função de callback para o selectbox
    def on_crypto_select_change():
        selected_name = st.session_state.cripto_select_outside_form
        try:
            st.session_state['selected_crypto_index'] = display_options.index(selected_name)
        except ValueError:
            st.session_state['selected_crypto_index'] = 0 # Fallback
        st.session_state['current_selected_crypto_obj'] = display_name_to_crypto_map.get(selected_name)

    # Inicializa o índice do selectbox ou usa o valor previamente selecionado
    if 'selected_crypto_index' not in st.session_state:
        st.session_state['selected_crypto_index'] = 0 # Define o primeiro item como padrão
        # Garante que o objeto da cripto inicial também seja definido
        if display_options:
            st.session_state['current_selected_crypto_obj'] = display_name_to_crypto_map.get(display_options[0])
        else:
            st.session_state['current_selected_crypto_obj'] = None


    # O selectbox exibirá apenas as strings de display_name
    selected_display_name = st.selectbox(
        "Criptomoeda", 
        options=display_options, 
        key="cripto_select_outside_form", # Chave diferente para estar fora do form
        help="Selecione a criptomoeda para a operação.",
        index=st.session_state['selected_crypto_index'], # Usa o índice do session_state
        on_change=on_crypto_select_change # Adiciona o callback aqui
    )

    # Recupera o objeto completo da criptomoeda selecionada do session_state para exibição
    # Agora, selected_crypto_for_display deve sempre refletir a seleção atual devido ao on_change
    selected_crypto_for_display = st.session_state.get('current_selected_crypto_obj')

    # Exibe a logo e o nome completo da criptomoeda selecionada abaixo do selectbox
    cripto_symbol = "" # Inicializa cripto_symbol
    if selected_crypto_for_display:
        st.markdown(
            f"<img src='{selected_crypto_for_display['image']}' width='30' height='30' style='vertical-align:middle; margin-right:10px;'> "
            f"**{selected_crypto_for_display['symbol']}** - {selected_crypto_for_display['name']}", 
            unsafe_allow_html=True
        )
        cripto_symbol = selected_crypto_for_display['symbol'] # Atribui o símbolo para uso posterior
    else:
        st.markdown("<p style='color:orange;'>Selecione uma criptomoeda para ver os detalhes.</p>", unsafe_allow_html=True)


    # Inicializa os valores do formulário no session_state se não existirem
    # Estes valores serão usados como 'value' para os widgets do formulário
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
            if not cripto_symbol:
                st.error("Por favor, selecione uma criptomoeda antes de registrar a operação.")
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
                    "cripto": str(cripto_symbol), # Garante que o símbolo é salvo como string
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
                                f"{op_details['cripto']} ({format_currency_brl(op_details['custo_total'])}) em "
                                f"{op_details['data_operacao'].strftime('%d/%m/%Y %H:%M')}")

                st.markdown(f"""
                <div style="background-color:#ffebeb; border:1px solid #ff0000; border-radius:5px; padding:10px; margin-bottom:20px;">
                    <h4 style="color:#ff0000; margin-top:0;'>⚠️ Confirmar Exclusão de Operação</h4>
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
        # Usar a lista completa de criptos para o filtro, se disponível
        # cryptocurrencies_data_df já é o DataFrame de criptos
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
        # Mapear símbolos para o objeto completo da criptomoeda
        # cryptocurrencies_data_df já é o DataFrame de criptos
        symbol_to_full_crypto_info_map = {crypto['symbol']: crypto for crypto in cryptocurrencies_data_df.to_dict('records')}
        
        # Criar novas colunas para a logo e o texto da cripto na tabela
        filtered_operations['crypto_image_html'] = filtered_operations['cripto'].apply(
            lambda symbol: f"<img src='{symbol_to_full_crypto_info_map[symbol]['image']}' width='20' height='20' style='vertical-align:middle; margin-right:5px;'>"
            if symbol and symbol in symbol_to_full_crypto_info_map and symbol_to_full_crypto_info_map[symbol].get('image') else "" 
        )
        filtered_operations['cripto_text_display'] = filtered_operations['cripto'].apply(
            lambda symbol: symbol_to_full_crypto_info_map[symbol]['display_name']
            if symbol and symbol in symbol_to_full_crypto_info_map else str(symbol)
        )

        # Definindo as colunas e seus respectivos ratios (ajustados para a nova coluna "Logo")
        col_names = [
            "Tipo", "Logo", "Cripto", "Qtd.", "PTAX",
            "Valor Total (USDT)", "Valor Total (BRL)", "P. Médio Compra",
            "P. Médio Venda", "Lucro/Prejuízo", "Data/Hora", "Origem", "Ações"
        ]
        # Ajustando os ratios das colunas para caber na tela
        # Total deve somar 1.0 ou próximo.
        cols_ratio = [0.05, 0.04, 0.08, 0.08, 0.06, 0.10, 0.10, 0.10, 0.10, 0.10, 0.07, 0.06, 0.06] 

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
            with cols[1]: # Nova coluna para a Logo
                st.markdown(op_row['crypto_image_html'], unsafe_allow_html=True)
            with cols[2]: # Coluna Cripto (apenas o texto)
                st.write(op_row['cripto_text_display'])
            with cols[3]:
                # Formatar a quantidade com ponto e vírgula do Brasil
                st.write(format_number_br(op_row['quantidade'], decimals=8)) 
            with cols[4]: # PTAX
                if pd.notna(op_row['ptax_na_op']):
                    # Formatar PTAX com 4 casas decimais
                    st.write(format_number_br(op_row['ptax_na_op'], decimals=4))
                else:
                    st.write("-")
            with cols[5]: # Valor Total (USDT)
                if is_foreign_wallet and pd.notna(op_row['custo_total_usdt']):
                    # Formatar Valor Total (USDT) com 2 casas decimais
                    st.write(f'USDT {format_number_br(op_row["custo_total_usdt"], decimals=2)}')
                else:
                    st.write("-")
            with cols[6]: # Valor Total (BRL)
                st.write(format_currency_brl(op_row['custo_total']))
            with cols[7]:
                if op_row['tipo_operacao'] == 'Compra' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(format_currency_brl(op_row['preco_medio_compra_na_op']))
                elif op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['preco_medio_compra_na_op']):
                    st.write(format_currency_brl(op_row['preco_medio_compra_na_op']))
                else:
                    st.write("-")
            with cols[8]:
                if op_row['tipo_operacao'] == 'Venda' and op_row['quantidade'] > 0:
                    st.write(format_currency_brl(op_row["custo_total"] / op_row["quantidade"]))
                else:
                    st.write("-")
            with cols[9]:
                if op_row['tipo_operacao'] == 'Venda' and pd.notna(op_row['lucro_prejuizo_na_op']):
                    profit_loss = op_row['lucro_prejuizo_na_op']
                    color = "green" if profit_loss >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>{format_currency_brl(profit_loss)}</span>", unsafe_allow_html=True)
                else:
                    st.write("-")
            with cols[10]:
                st.write(op_row['data_operacao'].strftime('%d/%m/%Y %H:%M'))
            with cols[11]:
                st.write(op_row['origem_carteira'])
            with cols[12]: # Coluna Ações
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

# A lógica de persistência de login é a maneira como você inicializa 'logged_in' e 'cpf'
# Se 'logged_in' já é True na sessão (o que acontece em uma atualização se não for resetado explicitamente),
# então o usuário permanece logado.
if st.session_state["logged_in"]:
    show_dashboard()
else:
    show_login()
