import requests
import json
import os # Importar para verificar existência do arquivo

def fetch_and_save_cryptos():
    """
    Busca a lista de criptomoedas de uma API (CoinGecko) e salva em cryptos.json.
    """
    # URL da API do CoinGecko para listar todas as criptomoedas
    # Esta API fornece o ID, símbolo e nome.
    url = "https://api.coingecko.com/api/v3/coins/list"
    
    try:
        print(f"Buscando dados de criptomoedas de: {url}")
        response = requests.get(url, timeout=20) # Aumentei o timeout para 20 segundos
        response.raise_for_status() # Levanta um erro para status de erro HTTP (4xx ou 5xx)
        data = response.json()

        cryptos_list = []
        for item in data:
            if 'symbol' in item and 'name' in item:
                # Formata como "SÍMBOLO - Nome Completo"
                cryptos_list.append(f"{item['symbol'].upper()} - {item['name']}")

        # Ordena a lista alfabeticamente para facilitar a busca no seletor
        cryptos_list.sort()

        # Define o nome do arquivo onde a lista será salva
        cryptos_file_name = "cryptos.json"

        # Salva a lista em formato JSON no arquivo
        with open(cryptos_file_name, "w", encoding="utf-8") as f:
            json.dump(cryptos_list, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Lista de criptomoedas atualizada e salva com sucesso em '{cryptos_file_name}'.")
        print(f"Total de criptomoedas salvas: {len(cryptos_list)}")

    except requests.exceptions.Timeout:
        print("❌ Erro: Tempo limite de conexão esgotado ao buscar dados da API. Tente novamente mais tarde.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar criptomoedas da API: {e}")
        print("Verifique sua conexão com a internet ou se a URL da API está correta.")
    except json.JSONDecodeError:
        print("❌ Erro ao decodificar a resposta JSON da API. A resposta pode não ser um JSON válido.")
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")

# Executa a função quando o script é rodado diretamente
if __name__ == "__main__":
    # Instale requests se ainda não tiver: pip install requests
    fetch_and_save_cryptos()
