import logging
from src.config import Config
from src.scraper import LiveloOfertasScraper, BlogTransferenciaScraper
from src.database import DatabaseManager
from src.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class AppOrchestrator:
    """Controla o fluxo principal: scrape → deduplica → salva → notifica."""

    def __init__(self, config: Config):
        self.config = config

    def executar(self):
        """Executa o pipeline completo de monitoramento."""
        logger.info("=== Iniciando monitoramento de promoções ===")

        # 1. Scrape das duas fontes
        todas_promocoes = []

        # Fonte 1: Ofertas da Livelo (pontos por real)
        try:
            scraper_ofertas = LiveloOfertasScraper(self.config.livelo_url)
            ofertas = scraper_ofertas.extrair_promocoes()
            todas_promocoes.extend(ofertas)
        except Exception as e:
            logger.error("Erro no scraper de ofertas: %s", e)

        # Fonte 2: Blog Melhores Destinos (bônus de transferência)
        try:
            scraper_blog = BlogTransferenciaScraper()
            transferencias = scraper_blog.extrair_promocoes()
            todas_promocoes.extend(transferencias)
        except Exception as e:
            logger.error("Erro no scraper do blog: %s", e)

        if not todas_promocoes:
            logger.info("Nenhuma promoção encontrada nesta execução")
            return

        logger.info("Total coletado: %d promoções", len(todas_promocoes))

        # 2. Deduplica + Salva + Notifica
        notifier = TelegramNotifier(
            self.config.telegram_token,
            self.config.telegram_chat_id,
        )
        novas = 0

        with DatabaseManager(self.config.database_url) as db:
            for promo in todas_promocoes:
                if db.promocao_existe(promo.promo_hash):
                    logger.debug("Já conhecida: [%s] %s", promo.tipo, promo.parceiro)
                    continue

                db.salvar_promocao(promo)
                notifier.enviar_alerta(promo)
                novas += 1

        logger.info(
            "=== Finalizado: %d novas de %d encontradas ===",
            novas,
            len(todas_promocoes),
        )
