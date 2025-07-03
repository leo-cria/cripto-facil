# coingecko_api_server.py
from flask import Flask, jsonify, request
import requests
import pandas as pd # Importa pandas
import os
import time
from datetime import datetime, timedelta # Para gerenciar a data do cache

app = Flask(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/list"
CACHE_FILE = "cryptocurrencies_cache.csv" # Nome do arquivo CSV para cache
CACHE_LIFETIME_HOURS = 24 # Tempo de vida do cache em horas (ex: 24 horas)

def load_cryptos_from_cache():
    """Tenta carregar as criptomoedas do cache CSV."""
    if os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE)
            # Verifica se o cache é recente
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
            if datetime.now() - file_mod_time < timedelta(hours=CACHE_LIFETIME_HOURS):
                print("Servindo criptomoedas do cache CSV.")
                return df.to_dict(orient='records')
            else:
                print("Cache CSV desatualizado.")
        except Exception as e:
            print(f"Erro ao ler cache CSV: {e}. Requisitando da API.")
    return None

def save_cryptos_to_cache(data):
    """Salva os dados das criptomoedas no cache CSV."""
    df = pd.DataFrame(data)
    df.to_csv(CACHE_FILE, index=False)
    print("Dados de criptomoedas salvos no cache CSV.")

@app.route('/cryptocurrencies', methods=['GET'])
def get_cryptocurrencies():
    """
    Endpoint para obter a lista de criptomoedas.
    Prioriza o cache CSV, depois busca do CoinGecko.
    """
    all_cryptos = load_cryptos_from_cache()

    if all_cryptos is None:
        try:
            print("Buscando criptomoedas da API CoinGecko...")
            response = requests.get(COINGECKO_API_URL)
            response.raise_for_status()
            all_cryptos = response.json()
            save_cryptos_to_cache(all_cryptos) # Salva no CSV após buscar
        except requests.exceptions.RequestException as e:
            print(f"Erro ao conectar com a API do CoinGecko: {e}")
            # Tenta carregar dados antigos do cache se houver erro com a API externa
            if os.path.exists(CACHE_FILE):
                try:
                    df = pd.read_csv(CACHE_FILE)
                    all_cryptos = df.to_dict(orient='records')
                    print("Erro no CoinGecko, servindo dados antigos do cache CSV.")
                except Exception as e_cache:
                    return jsonify({"error": f"Erro grave: Não foi possível obter dados do CoinGecko nem do cache: {e_cache}"}), 500
            else:
                return jsonify({"error": f"Erro ao buscar criptomoedas da fonte externa: {e}"}), 500
        except Exception as e:
            print(f"Ocorreu um erro inesperado na API local: {e}")
            return jsonify({"error": f"Ocorreu um erro interno: {e}"}), 500

    # Opcional: Adicionar funcionalidade de busca
    search_query = request.args.get('search', '').lower()
    if search_query:
        # Garante que 'all_cryptos' é uma lista de dicionários
        if not isinstance(all_cryptos, list):
             # Isso só deve acontecer se load_cryptos_from_cache ou CoinGecko retornarem algo inesperado
            return jsonify({"error": "Formato de dados inesperado da fonte de criptomoedas."}), 500

        filtered_cryptos = [
            crypto for crypto in all_cryptos
            if search_query in crypto.get('id', '').lower() or
               search_query in crypto.get('symbol', '').lower() or
               search_query in crypto.get('name', '').lower()
        ]
        return jsonify(filtered_cryptos)

    return jsonify(all_cryptos)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
