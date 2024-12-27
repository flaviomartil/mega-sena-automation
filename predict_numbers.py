import pandas as pd
import numpy as np
import mysql.connector
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import random
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    filename='megasena_logs.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Função para conectar ao banco de dados
def conectar_banco():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="user",
            password="userpassword",
            database="megasena",
            port=3309
        )
        logging.info("Conexão com o banco de dados estabelecida com sucesso.")
        return conn
    except mysql.connector.Error as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

# Função para criar a tabela de previsões
def criar_tabela_previsoes(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS previsoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data_previsao DATETIME,
                numero_previsto INT,
                combinacao_sugerida VARCHAR(255)
            )
        ''')
        conn.commit()
        logging.info("Tabela 'previsoes' criada/verificada com sucesso.")
    except mysql.connector.Error as e:
        logging.error(f"Erro ao criar/verificar tabela 'previsoes': {e}")
        raise

# Função para salvar previsões no banco
def salvar_previsao(conn, numero_previsto, combinacoes):
    try:
        cursor = conn.cursor()
        data_previsao = datetime.now()
        for combinacao in combinacoes:
            combinacao_str = ' '.join(map(str, combinacao))
            cursor.execute('''
                INSERT INTO previsoes (data_previsao, numero_previsto, combinacao_sugerida)
                VALUES (%s, %s, %s)
            ''', (data_previsao, numero_previsto, combinacao_str))
        conn.commit()
        logging.info("Previsões salvas com sucesso no banco de dados.")
    except mysql.connector.Error as e:
        logging.error(f"Erro ao salvar previsões no banco de dados: {e}")
        raise

# Função para preparar os dados para o modelo LSTM
def preparar_dados_lstm(numeros, seq_length):
    X, y = [], []
    for i in range(len(numeros) - seq_length):
        X.append(numeros[i:i + seq_length])
        y.append(numeros[i + seq_length])
    return np.array(X), np.array(y)

# Função para gerar combinações sugeridas
def gerar_combinacoes(numeros, num_combinacoes=20):
    return [sorted(random.sample(numeros, 6)) for _ in range(num_combinacoes)]

# Início do script
try:
    # Conectar ao banco
    conn = conectar_banco()

    # Criar tabela de previsões
    criar_tabela_previsoes(conn)

    # Extrair dados do banco
    query = 'SELECT concurso, data, numeros FROM resultados'
    df = pd.read_sql(query, con=conn)
    logging.info("Dados históricos extraídos do banco de dados com sucesso.")

    # Converter e preparar os dados
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])

    numeros_separados = df['numeros'].str.split(' ', expand=True)
    numeros_separados.columns = [f'num{i+1}' for i in range(numeros_separados.shape[1])]
    numeros_separados = numeros_separados.apply(pd.to_numeric)

    todos_numeros = pd.concat([numeros_separados[f'num{i+1}'] for i in range(6)])
    frequencia_numeros = todos_numeros.value_counts().sort_index()

    # Normalizar os dados
    scaler = MinMaxScaler(feature_range=(0, 1))
    numeros_normalizados = scaler.fit_transform(todos_numeros.values.reshape(-1, 1))

    # Preparar os dados para o modelo LSTM
    seq_length = 6
    X, y = preparar_dados_lstm(numeros_normalizados, seq_length)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    # Construção do modelo LSTM
    modelo = Sequential()
    modelo.add(LSTM(50, return_sequences=True, input_shape=(seq_length, 1)))
    modelo.add(LSTM(50))
    modelo.add(Dense(1))
    modelo.compile(optimizer='adam', loss='mean_squared_error')

    # Treinar o modelo
    modelo.fit(X, y, epochs=20, batch_size=32, verbose=1)
    logging.info("Modelo LSTM treinado com sucesso.")

    # Fazer previsão
    previsao_normalizada = modelo.predict(X[-1].reshape(1, seq_length, 1))
    previsao = int(scaler.inverse_transform(previsao_normalizada)[0][0])
    logging.info(f"Número previsto: {previsao}")

    # Gerar combinações sugeridas
    numeros_mais_frequentes = frequencia_numeros.nlargest(15).index.tolist()
    combinacoes_sugeridas = gerar_combinacoes(numeros_mais_frequentes)
    for i, combinacao in enumerate(combinacoes_sugeridas, 1):
        logging.info(f"Combinação sugerida {i}: {combinacao}")

    # Salvar previsões no banco
    salvar_previsao(conn, previsao, combinacoes_sugeridas)

except Exception as e:
    logging.error(f"Erro geral no script: {str(e)}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        logging.info("Conexão com o banco de dados fechada.")
