import sqlite3

class Connection:
    """
    Gerencia a conexão com o banco de dados
    """
    def __init__(self, db_name="database.db"):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()