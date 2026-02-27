import os
import logging

logger = logging.getLogger(__name__)

LIVELO_URL_DEFAULT = "https://www.livelo.com.br/ofertas"


class Config:
    """Configuração centralizada carregada de variáveis de ambiente."""

    def __init__(self):
        self.database_url = self._exigir("DATABASE_URL")
        self.telegram_token = self._exigir("TELEGRAM_TOKEN")
        self.telegram_chat_id = self._exigir("TELEGRAM_CHAT_ID")
        self.livelo_url = os.getenv("LIVELO_URL", LIVELO_URL_DEFAULT)
        logger.info("Configuração carregada com sucesso")

    @staticmethod
    def _exigir(nome: str) -> str:
        """Exige que a variável de ambiente exista."""
        valor = os.getenv(nome)
        if not valor:
            raise EnvironmentError(
                f"Variável de ambiente obrigatória não definida: {nome}"
            )
        return valor
