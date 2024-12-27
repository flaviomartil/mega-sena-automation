from datetime import datetime
import requests
import mysql.connector
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

BASE_URL = "https://api.guidi.dev.br/loteria/megasena/{concurso}"
ULTIMO_URL = "https://api.guidi.dev.br/loteria/megasena/ultimo"

# Bloqueio para sincronizar o acesso ao banco de dados
db_lock = threading.Lock()

def criar_banco():
    """Cria a tabela no banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="user",
            password="userpassword",
            database="megasena",
            port=3309
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resultados (
                concurso INT PRIMARY KEY,
                data DATE,
                numeros VARCHAR(255)
            )
        ''')
        conn.commit()
        print("Tabela criada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro ao criar tabela: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def salvar_resultado(concurso, data, numeros):
    """Salva o resultado no banco de dados."""
    with db_lock:  # Garante que apenas uma thread acesse o banco
        try:
            # Converte a data de dd/mm/yyyy para yyyy-mm-dd
            try:
                data_formatada = datetime.strptime(data, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                print(f"Data inválida para o concurso {concurso}: {data}")
                return

            conn = mysql.connector.connect(
                host="localhost",
                user="user",
                password="userpassword",
                database="megasena",
                port=3309
            )
            cursor = conn.cursor()
            cursor.execute('''
                INSERT IGNORE INTO resultados (concurso, data, numeros)
                VALUES (%s, %s, %s)
            ''', (concurso, data_formatada, numeros))
            conn.commit()
            print(f"Concurso {concurso} salvo com sucesso no banco.")
        except mysql.connector.Error as err:
            print(f"Erro ao salvar concurso {concurso}: {err}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                conn.close()

def obter_ultimo_concurso():
    """Obtém o número do último concurso disponível."""
    try:
        response = requests.get(ULTIMO_URL)
        response.raise_for_status()
        dados = response.json()
        return dados['numero']
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter o último concurso: {e}")
        raise
    except KeyError:
        print("Erro: A resposta não contém a chave 'numero'.")
        raise

def processar_concurso(concurso):
    """Faz a requisição para um concurso específico e salva o resultado."""
    url = BASE_URL.format(concurso=concurso)
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return f"Concurso {concurso} não encontrado."
        
        response.raise_for_status()
        dados = response.json()

        # Validação do tipo de jogo
        if dados.get('tipoJogo') != "MEGA_SENA":
            return f"Concurso {concurso} não é Mega Sena."

        # Validação dos dados retornados
        if 'listaDezenas' not in dados or 'dataApuracao' not in dados:
            return f"Concurso {concurso}: Dados incompletos."

        numeros = " ".join(dados['listaDezenas'])
        data = dados['dataApuracao']  # Data no formato dd/mm/yyyy

        salvar_resultado(concurso, data, numeros)
        return f"Concurso {concurso}: Data: {data}, Números: {numeros}"

    except requests.exceptions.RequestException as e:
        return f"Erro ao processar concurso {concurso}: {e}"

def obter_resultados():
    """Obtém todos os resultados paralelamente."""
    ultimo_concurso = obter_ultimo_concurso()
    print(f"Último concurso encontrado: {ultimo_concurso}")

    concursos = range(1, ultimo_concurso + 1)
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(processar_concurso, concurso): concurso for concurso in concursos}

        for future in as_completed(futures):
            concurso = futures[future]
            try:
                resultado = future.result()
                print(resultado)
            except Exception as e:
                print(f"Erro no concurso {concurso}: {e}")

if __name__ == "__main__":
    criar_banco()
    inicio = time.time()
    obter_resultados()
    print(f"Processo concluído em {time.time() - inicio:.2f} segundos.")
