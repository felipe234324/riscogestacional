import sqlite3

def criar_banco():
    try:
        conn = sqlite3.connect('banco.db')
        cursor = conn.cursor()
        print("Conectado ao banco de dados 'banco.db'.")

        # Criando a tabela calculos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_ficha TEXT NOT NULL,
            nome_gestante TEXT NOT NULL,
            data_nasc TEXT NOT NULL,
            cpf TEXT,
            telefone TEXT,
            municipio TEXT NOT NULL,
            ubs TEXT,
            acs TEXT,
            periodo_gestacional TEXT,
            data_envio TEXT,
            pontuacao_total INTEGER,
            classificacao_risco TEXT,
            imc REAL,
            caracteristicas TEXT,
            avaliacao_nutricional TEXT,
            comorbidades TEXT,
            historia_obstetrica TEXT,
            condicoes_gestacionais TEXT,
            profissional TEXT,
            ativo INTEGER DEFAULT 1
        )
        ''')
        print("Tabela 'calculos' verificada/criada.")

        # Migração para adicionar a coluna cpf
        try:
            cursor.execute('ALTER TABLE calculos ADD COLUMN cpf TEXT')
            print("Coluna 'cpf' adicionada à tabela 'calculos'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'cpf' já existe na tabela 'calculos'.")
            else:
                print(f"Erro ao adicionar coluna 'cpf': {str(e)}")

        # Migração para adicionar a coluna ativo
        try:
            cursor.execute('ALTER TABLE calculos ADD COLUMN ativo INTEGER DEFAULT 1')
            print("Coluna 'ativo' adicionada à tabela 'calculos'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Coluna 'ativo' já existe na tabela 'calculos'.")
            else:
                print(f"Erro ao adicionar coluna 'ativo': {str(e)}")

        # Atualizar registros antigos com CPF padrão
        try:
            cursor.execute('UPDATE calculos SET cpf = "000.000.000-00" WHERE cpf IS NULL OR cpf = ""')
            print("Registros antigos em 'calculos' atualizados com CPF padrão '000.000.000-00'.")
        except sqlite3.OperationalError as e:
            print(f"Erro ao atualizar CPFs antigos em 'calculos': {str(e)}")

        # Atualizar registros com municipio nulo ou vazio
        try:
            cursor.execute('UPDATE calculos SET municipio = "Itaquitinga" WHERE municipio IS NULL OR municipio = ""')
            print("Registros em 'calculos' com município nulo ou vazio atualizados para 'Itaquitinga'.")
        except sqlite3.OperationalError as e:
            print(f"Erro ao atualizar municípios em 'calculos': {str(e)}")

        conn.commit()
        print("Banco de dados e tabelas inicializados com sucesso.")

    except sqlite3.Error as e:
        print(f"Erro ao configurar o banco de dados: {str(e)}")
        raise
    finally:
        conn.close()
        print("Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    criar_banco()