import logging
from src.config import Config
from src.scraper import LiveloScraper
from src.database import DatabaseManager
from src.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class AppOrchestrator:
    """Controla o fluxo principal: scrape → deduplica → salva → notifica."""

    def __init__(self, config: Config):
        self.config = config

    def executar(self):
        """Executa o pipeline completo de monitoramento."""
        logger.info("=== Iniciando monitoramento de promoções Livelo ===")

        # 1. Scrape
        scraper = LiveloScraper(self.config.livelo_url)
        promocoes = scraper.extrair_promocoes()

        if not promocoes:
            logger.info("Nenhuma promoção encontrada nesta execução")
            return

        # 2. Deduplica + Salva + Notifica
        notifier = TelegramNotifier(
            self.config.telegram_token,
            self.config.telegram_chat_id,
        )
        novas = 0

        with DatabaseManager(self.config.database_url) as db:
            for promo in promocoes:
                if db.promocao_existe(promo.promo_hash):
                    logger.debug("Promoção já conhecida: %s", promo.parceiro)
                    continue

                db.salvar_promocao(promo)
                notifier.enviar_alerta(promo)
                novas += 1

        logger.info(
            "=== Finalizado: %d novas promoções de %d encontradas ===",
            novas,
            len(promocoes),
        )
