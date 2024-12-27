import mysql.connector
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de variáveis do .env
EMAIL = os.getenv("EMAIL")  # Seu e-mail para enviar
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Senha do aplicativo
JOGOS = os.getenv("JOGOS").split('|')  # Lista de jogos do .env
DATA_APURACAO = os.getenv("DATA_APURACAO")  # Data de apuração do .env

# Ajustar DATA_APURACAO para o formato MySQL (yyyy-mm-dd)
DATA_APURACAO_FORMATADA = datetime.strptime(DATA_APURACAO, "%d/%m/%Y").strftime("%Y-%m-%d")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT"))

def conectar_banco():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        print("Conexão com o banco de dados estabelecida.")
        return conn
    except mysql.connector.Error as e:
        print(f"Erro ao conectar no banco de dados: {e}")
        raise

# Função para enviar e-mail
def enviar_email(assunto, mensagem, destinatario):
    try:
        msg = MIMEText(mensagem)
        msg["Subject"] = assunto
        msg["From"] = EMAIL
        msg["To"] = destinatario

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            server.sendmail(EMAIL, destinatario, msg.as_string())

        print(f"E-mail enviado com sucesso para {destinatario}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

# Criar tabela de jogos jogados
def criar_tabela_jogos(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogos_jogados (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numeros_jogados VARCHAR(255) UNIQUE,
                acertos INT,
                data_comparacao DATE
            )
        ''')
        conn.commit()
        print("Tabela 'jogos_jogados' criada/verificada com sucesso.")
    except mysql.connector.Error as e:
        print(f"Erro ao criar tabela: {e}")
        raise

# Obter último sorteio pela API
def obter_ultimo_sorteio():
    try:
        url = "https://api.guidi.dev.br/loteria/megasena/ultimo"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        sorteio = list(map(int, data["listaDezenas"]))
        data_apuracao = data["dataApuracao"]
        print(f"Último sorteio: {sorteio}, Data de apuração: {data_apuracao}")
        return sorteio, datetime.strptime(data_apuracao, "%d/%m/%Y").strftime("%Y-%m-%d")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter último sorteio: {e}")
        raise

# Comparar jogos com o último sorteio
def comparar_jogos(jogos, sorteio):
    resultados = []
    for jogo in jogos:
        numeros = list(map(int, jogo.split(',')))
        acertos = len(set(numeros) & set(sorteio))
        resultados.append({
            "numeros": jogo,
            "acertos": acertos,
            "data_comparacao": DATA_APURACAO_FORMATADA
        })
    print(f"Resultados comparados: {resultados}")
    return resultados

# Verificar se o jogo já foi processado
def jogo_existe(conn, jogo, data_apuracao):
    try:
        cursor = conn.cursor()
        query = '''
            SELECT COUNT(*) FROM jogos_jogados WHERE numeros_jogados = %s AND data_comparacao = %s
        '''
        cursor.execute(query, (jogo, data_apuracao))
        resultado = cursor.fetchone()[0]
        print(f"Jogo '{jogo}' já existe: {resultado > 0}")
        return resultado > 0
    except mysql.connector.Error as e:
        print(f"Erro ao verificar se o jogo existe: {e}")
        raise

# Inserir resultados no banco
def inserir_jogos(conn, jogos):
    try:
        cursor = conn.cursor()
        for jogo in jogos:
            if not jogo_existe(conn, jogo['numeros'], jogo['data_comparacao']):
                query = '''
                    INSERT INTO jogos_jogados (numeros_jogados, acertos, data_comparacao)
                    VALUES (%s, %s, %s)
                '''
                cursor.execute(query, (jogo['numeros'], jogo['acertos'], jogo['data_comparacao']))
                conn.commit()
                print(f"Jogo inserido: {jogo['numeros']} | Acertos: {jogo['acertos']}")
            else:
                print(f"Jogo já existe no banco: {jogo['numeros']}")
    except mysql.connector.Error as e:
        print(f"Erro ao inserir jogos: {e}")
        raise

# Enviar e-mail com resultados
# Enviar e-mail com resultados
def enviar_email_resultados(resultados):
    mensagem = f"Resultados do sorteio ({DATA_APURACAO}):\n\n"
    for resultado in resultados:
        # Determinar o tipo de premiação
        if resultado['acertos'] == 6:
            tipo = "Sena"
        elif resultado['acertos'] == 5:
            tipo = "Quina"
        elif resultado['acertos'] == 4:
            tipo = "Quadra"
        else:
            tipo = "Sem prêmio"

        mensagem += f"Jogo: {resultado['numeros']} | Acertos: {resultado['acertos']} | Prêmio: {tipo}\n"

    # Enviar o e-mail
    enviar_email("Resultados Mega-Sena", mensagem, EMAIL)

# Script principal
try:
    conn = conectar_banco()

    # Criar tabela de jogos jogados
    criar_tabela_jogos(conn)

    # Obter o último sorteio
    ultimo_sorteio, data_apuracao_api = obter_ultimo_sorteio()

    # Verificar se a data de apuração no .env coincide com a da API
    if DATA_APURACAO_FORMATADA == data_apuracao_api:
        resultados = comparar_jogos(JOGOS, ultimo_sorteio)

        # Filtrar jogos não processados
        novos_resultados = [r for r in resultados if not jogo_existe(conn, r['numeros'], DATA_APURACAO_FORMATADA)]

        if novos_resultados:
            # Inserir no banco e enviar e-mail
            inserir_jogos(conn, novos_resultados)
            enviar_email_resultados(novos_resultados)
        else:
            print("Nenhum novo jogo para processar.")
    else:
        print(f"Data de apuração no .env ({DATA_APURACAO_FORMATADA}) não coincide com a API ({data_apuracao_api}).")

except Exception as e:
    print(f"Erro geral no script: {e}")
finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("Conexão com o banco de dados encerrada.")
