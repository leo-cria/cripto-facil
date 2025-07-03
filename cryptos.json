import requests
import json
import time

def fetch_and_save_cryptos():
    url = "https://api.coingecko.com/api/v3/coins/list" # Exemplo de API do CoinGecko
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Levanta um erro para status de erro HTTP
        data = response.json()

        # Filtrar e formatar para 'SÍMBOLO - Nome (ID)' ou apenas 'SÍMBOLO'
        # Dependendo de como você quer exibir.
        # Para um seletor simples, apenas o símbolo é geralmente suficiente.
        # Se quiser nome completo, ajuste o formato.
        cryptos = []
        for item in data:
            if 'symbol' in item and 'name' in item:
                # Pegando apenas as mais relevantes, ou pode processar todas
                cryptos.append(f"{item['symbol'].upper()} - {item['name']}")

        # Ou apenas os símbolos:
        # cryptos = [item['symbol'].upper() for item in data if 'symbol' in item]


        # Salva em um arquivo JSON
        with open("cryptos.json", "w", encoding="utf-8") as f:
            json.dump(sorted(cryptos), f, ensure_ascii=False, indent=4)
        print("Lista de criptomoedas atualizada e salva em cryptos.json")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar criptomoedas da API: {e}")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# Execute este script periodicamente (ex: com um cron job)
if __name__ == "__main__":
    fetch_and_save_cryptos()
