import logging
import sys
from dotenv import load_dotenv
from src.config import Config
from src.orchestrator import AppOrchestrator


def configurar_logging():
    """Configura o sistema de logging para console (stdout)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    configurar_logging()
    logger = logging.getLogger(__name__)

    try:
        load_dotenv()
        config = Config()
        app = AppOrchestrator(config)
        app.executar()
    except EnvironmentError as e:
        logger.critical("Erro de configuração: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.critical("Erro fatal: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
