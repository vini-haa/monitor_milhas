import logging
import psycopg2
from src.models import Promocao

logger = logging.getLogger(__name__)

SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS promocoes (
    id SERIAL PRIMARY KEY,
    parceiro VARCHAR(100) NOT NULL,
    bonus_percentual INTEGER NOT NULL,
    data_inicio VARCHAR(50),
    data_fim VARCHAR(50),
    url TEXT,
    tipo VARCHAR(20) NOT NULL DEFAULT 'oferta',
    descricao TEXT DEFAULT '',
    promo_hash VARCHAR(64) UNIQUE NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
"""

SQL_VERIFICAR_HASH = "SELECT 1 FROM promocoes WHERE promo_hash = %s"

SQL_INSERIR = """
INSERT INTO promocoes (parceiro, bonus_percentual, data_inicio, data_fim, url, tipo, descricao, promo_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


class DatabaseManager:
    """Gerencia conexão e operações CRUD no PostgreSQL (Neon.tech)."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None

    def conectar(self):
        """Abre conexão com o PostgreSQL."""
        logger.info("Conectando ao PostgreSQL...")
        self.conn = psycopg2.connect(self.database_url)
        self.conn.autocommit = True
        logger.info("Conexão estabelecida com sucesso")

    def criar_tabela(self):
        """Cria a tabela de promoções se não existir (migration automática)."""
        with self.conn.cursor() as cur:
            cur.execute(SQL_CRIAR_TABELA)
        logger.info("Tabela 'promocoes' verificada/criada")

    def promocao_existe(self, promo_hash: str) -> bool:
        """Verifica se uma promoção já existe no banco pelo hash."""
        with self.conn.cursor() as cur:
            cur.execute(SQL_VERIFICAR_HASH, (promo_hash,))
            return cur.fetchone() is not None

    def salvar_promocao(self, promo: Promocao):
        """Insere uma nova promoção no banco de dados."""
        with self.conn.cursor() as cur:
            cur.execute(SQL_INSERIR, (
                promo.parceiro,
                promo.bonus_percentual,
                promo.data_inicio,
                promo.data_fim,
                promo.url,
                promo.tipo,
                promo.descricao,
                promo.promo_hash,
            ))
        logger.info("Promoção salva: [%s] %s (%d%%)", promo.tipo, promo.parceiro, promo.bonus_percentual)

    def fechar(self):
        """Fecha a conexão com o banco."""
        if self.conn:
            self.conn.close()
            logger.info("Conexão com o banco fechada")

    def __enter__(self):
        self.conectar()
        self.criar_tabela()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fechar()
