import requests
import json
import os
import time
from datetime import datetime

def fetch_and_save_cryptos():
    """
    Busca o máximo possível de criptomoedas da API do CoinGecko, sem filtros de símbolos,
    e salva em cryptos.json, aplicando ordenação e adicionando a data da atualização.
    """
    base_url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "brl",
        "order": "market_cap_desc", # Ordena por capitalização de mercado (maiores primeiro)
        "per_page": 250, # Máximo permitido por requisição
        "sparkline": "false" # Não carrega dados de gráfico desnecessários
    }

    all_cryptos_raw_data = [] # Armazena os dados brutos de todas as chamadas da API
    page = 1
    # Definindo um limite alto de páginas para buscar o máximo possível.
    # O número real de criptomoedas pode ser menor se a API não tiver dados para todas as páginas.
    max_pages_to_fetch = 200 # Aumentado para 200 páginas, conforme solicitado (200 * 250 = 50.000 potenciais entradas)

    print("Iniciando a busca de criptomoedas da CoinGecko API (sem filtros de símbolos)...")
    print(f"Tentando buscar até {max_pages_to_fetch} páginas, com 250 criptos por página.")

    while page <= max_pages_to_fetch:
        params["page"] = page
        try:
            print(f"Buscando página {page} de criptomoedas...")
            response = requests.get(base_url, params=params, timeout=45) # Aumentado o timeout para 45 segundos
            response.raise_for_status() # Levanta um erro para status de erro HTTP (4xx ou 5xx)
            data = response.json()

            if not data:
                print(f"Nenhum dado encontrado na página {page}. Encerrando a busca por páginas.")
                break # Sai do loop se a página não retornar dados (indicando o fim dos resultados)

            all_cryptos_raw_data.extend(data)
            print(f"Página {page} buscada com sucesso. Total de itens brutos coletados até agora: {len(all_cryptos_raw_data)}")
            page += 1
            time.sleep(1.5) # Aumentado o delay para 1.5 segundos para ser mais seguro com mais requisições

        except requests.exceptions.Timeout:
            print(f"❌ Erro: Tempo limite de conexão esgotado na página {page}. Aumentando o delay e tentando a próxima página.")
            page += 1
            time.sleep(5) # Pausa maior em caso de timeout
            continue # Continua para a próxima página mesmo após timeout
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao buscar criptomoedas da API na página {page}: {e}")
            print("Verifique sua conexão com a internet ou se a URL da API está correta. Encerrando a busca.")
            break # Sai do loop em caso de erro de requisição
        except json.JSONDecodeError:
            print(f"❌ Erro ao decodificar a resposta JSON da API na página {page}. A resposta pode não ser um JSON válido. Encerrando a busca.")
            break # Sai do loop em caso de erro de decodificação JSON
        except Exception as e:
            print(f"❌ Ocorreu um erro inesperado na página {page}: {e}. Encerrando a busca.")
            break # Sai do loop em caso de qualquer outro erro inesperado

    cryptos_list_formatted = []
    # Usar um conjunto para rastrear símbolos já adicionados e evitar duplicatas
    seen_symbols = set()

    for item in all_cryptos_raw_data:
        # Verifica se os campos essenciais existem
        if 'symbol' in item and 'name' in item and 'image' in item and 'current_price' in item:
            symbol = item['symbol'].upper()
            name = item['name']
            image_url = item['image']
            current_price_brl = item['current_price']

            # --- FILTROS DE SÍMBOLOS REMOVIDOS AQUI ---
            # As linhas de 're.match' e 'len(symbol)' foram removidas para incluir o máximo de criptos.

            # Evita duplicatas, mantendo a primeira ocorrência (que deve ser a de maior capitalização de mercado devido à ordem da API)
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)

            # Adiciona um dicionário com os detalhes da criptomoeda
            cryptos_list_formatted.append({
                "symbol": symbol,
                "name": name,
                "image": image_url,
                "display_name": f"{symbol} - {name}",  # Nome para exibição
                "current_price_brl": current_price_brl # Preço atual em BRL
            })

    # Função de chave personalizada para ordenação:
    # 1. Criptos que começam com letras vêm primeiro (ordenadas alfabeticamente).
    # 2. Criptos que começam com números vêm depois (ordenadas por seu valor numérico, se aplicável, ou como string).
    def sort_key(crypto):
        symbol = crypto['symbol']
        if symbol and symbol[0].isalpha():
            return (0, symbol)  # Letras vêm antes (0)
        else:
            return (1, symbol)  # Números e outros caracteres vêm depois (1)

    cryptos_list_formatted.sort(key=sort_key)

    # Adiciona a data e hora da atualização ao dicionário JSON
    update_info = {
        "last_updated_timestamp": datetime.now().isoformat(),
        "cryptos": cryptos_list_formatted
    }

    cryptos_file_name = "cryptos.json"

    try:
        with open(cryptos_file_name, "w", encoding="utf-8") as f:
            json.dump(update_info, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Lista de criptomoedas atualizada e salva com sucesso em '{cryptos_file_name}'.")
        print(f"Total de criptomoedas salvas: {len(cryptos_list_formatted)}")
    except IOError as e:
        print(f"❌ Erro de I/O ao salvar '{cryptos_file_name}': {e}. Verifique as permissões de escrita.")
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado ao salvar o arquivo JSON: {e}")


# Executa a função quando o script é rodado diretamente
if __name__ == "__main__":
    fetch_and_save_cryptos()
