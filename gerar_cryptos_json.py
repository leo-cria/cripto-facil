import requests
import time
import json
import os
from datetime import datetime

# Nome do arquivo onde os dados serão salvos
CRYPTOS_FILE = "cryptos.json"

# Configurações da API CoinGecko
BASE_URL = "https://api.coingecko.com/api/v3"
MARKETS_ENDPOINT = "/coins/markets"
VS_CURRENCY = "brl"  # Moeda de comparação, consistente com app.py
PER_PAGE = 250  # Máximo de itens por página permitido pela CoinGecko
TOTAL_PAGES_TO_FETCH = 40  # Total de páginas que você deseja buscar (ALTERADO PARA 40)
PAGES_PER_BLOCK = 4  # Número de páginas a buscar por bloco
MAX_RETRIES = 5  # Número máximo de retentativas para uma página com erro (incluindo a primeira tentativa)
RETRY_DELAY_SECONDS = 10  # Atraso entre as retentativas (pode ser maior para 429)
NORMAL_DELAY_SECONDS = 5  # Atraso normal entre as requisições para respeitar o rate limit


def fetch_and_save_crypto_data():
    """
    Busca dados de criptomoedas da API da CoinGecko em blocos de páginas,
    com retentativas em caso de erro, e os salva em um arquivo JSON.
    """
    all_cryptos_data = []

    print(
        f"🚀 Iniciando a coleta de criptomoedas em blocos de {PAGES_PER_BLOCK} páginas (até a página {TOTAL_PAGES_TO_FETCH})...")

    # Loop principal para iterar por todas as páginas
    for page in range(1, TOTAL_PAGES_TO_FETCH + 1):
        print(f"🔄 Buscando página {page}...")

        retries = 0
        success = False
        while retries < MAX_RETRIES and not success:
            try:
                url = f"{BASE_URL}{MARKETS_ENDPOINT}"
                params = {
                    'vs_currency': VS_CURRENCY,
                    'order': 'market_cap_desc',  # Busca por capitalização de mercado (lista completa)
                    'per_page': PER_PAGE,
                    'page': page,
                    'sparkline': 'false'
                }

                response = requests.get(url, params=params)

                if response.status_code == 429:
                    print(
                        f"⛔ Erro 429 (Rate Limit) na página {page}. Tentativa {retries + 1}/{MAX_RETRIES}. Pausando 60 segundos.")
                    time.sleep(60)  # Pausa mais longa para rate limit
                    retries += 1
                    continue  # Tenta a mesma página novamente

                response.raise_for_status()  # Lança um erro para outros status HTTP ruins (4xx ou 5xx)

                coins = response.json()

                if not coins:
                    print(
                        f"⚠️ Página {page} retornou vazia. Pode ser o fim dos dados ou um erro inesperado. Prosseguindo.")
                    success = True  # Considera como sucesso para não travar, mas alerta
                    break  # Sai do loop de retentativas para esta página

                # Processa os dados para o formato desejado pelo app.py
                for coin in coins:
                    # Garantir que os campos existem antes de acessar
                    symbol = coin.get('symbol', '').upper()
                    name = coin.get('name', '')
                    image = coin.get('image', '')
                    current_price = coin.get('current_price', 0.0)

                    all_cryptos_data.append({
                        'symbol': symbol,
                        'name': name,
                        'image': image,
                        'display_name': f"{symbol} - {name}",
                        'current_price_brl': current_price  # Já está em BRL se VS_CURRENCY='brl'
                    })

                print(
                    f"✅ Página {page} buscada com sucesso. Total de criptos coletadas até agora: {len(all_cryptos_data)}")
                success = True  # Marca como sucesso para sair do loop de retentativas

            except requests.exceptions.RequestException as e:
                print(f"❗ Erro de requisição na página {page} (tentativa {retries + 1}/{MAX_RETRIES}): {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    print(f"Aguardando {RETRY_DELAY_SECONDS} segundos para retentar...")
                    time.sleep(RETRY_DELAY_SECONDS)
            except json.JSONDecodeError as e:
                print(f"❗ Erro ao decodificar JSON da página {page} (tentativa {retries + 1}/{MAX_RETRIES}): {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    print(f"Aguardando {RETRY_DELAY_SECONDS} segundos para retentar...")
                    time.sleep(RETRY_DELAY_SECONDS)
            except Exception as e:
                print(f"❗ Erro inesperado ao buscar página {page} (tentativa {retries + 1}/{MAX_RETRIES}): {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    print(f"Aguardando {RETRY_DELAY_SECONDS} segundos para retentar...")
                    time.sleep(RETRY_DELAY_SECONDS)

        if not success:
            print(
                f"❌ Falha persistente ao buscar página {page} após {MAX_RETRIES} retentativas. Pulando para a próxima página.")

        # Pausa normal entre as requisições para respeitar o rate limit da CoinGecko
        time.sleep(NORMAL_DELAY_SECONDS)

        # Lógica para "blocos de 4 em 4 páginas" para logging/feedback
        if page % PAGES_PER_BLOCK == 0:
            print(f"\n--- Bloco de {PAGES_PER_BLOCK} páginas concluído (até página {page}). ---")
            if page < TOTAL_PAGES_TO_FETCH:  # Se não for o último bloco
                print(f"Aguardando 60 segundos antes do próximo bloco de páginas...")
                time.sleep(60)  # Pausa maior entre blocos

    # NOVO: Imprime o total de criptos coletadas antes de salvar
    print(f"\n✅ Coleta finalizada. Total de criptos coletadas antes de salvar: {len(all_cryptos_data)}")

    # Salva todos os dados coletados em um único arquivo JSON
    final_data_structure = {
        "last_updated_timestamp": datetime.now().isoformat(),
        "cryptos": all_cryptos_data
    }

    try:
        with open(CRYPTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data_structure, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Dados de {len(all_cryptos_data)} criptomoedas salvos com sucesso em {CRYPTOS_FILE}")
    except IOError as e:
        print(f"❌ Erro ao salvar os dados no arquivo {CRYPTOS_FILE}: {e}")


if __name__ == "__main__":
    fetch_and_save_crypto_data()