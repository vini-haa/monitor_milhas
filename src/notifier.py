import logging
import time
import requests
from src.models import Promocao

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_TENTATIVAS = 3


class TelegramNotifier:
    """Envia alertas formatados de promoções via Telegram Bot API."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = TELEGRAM_API.format(token=token)

    def _formatar_mensagem(self, promo: Promocao) -> str:
        """Formata a promoção como mensagem HTML para o Telegram."""
        if promo.tipo == "transferencia":
            return (
                f"<b>Bonus de Transferencia!</b>\n\n"
                f"<b>Programa:</b> {promo.parceiro}\n"
                f"<b>Bonus:</b> {promo.bonus_percentual}%\n"
                f"<b>Periodo:</b> {promo.data_inicio} ate {promo.data_fim}\n"
                f"<b>Fonte:</b> {promo.descricao[:100]}\n\n"
                f'<a href="{promo.url}">Ver detalhes</a>'
            )
        else:
            return (
                f"<b>Oferta Livelo!</b>\n\n"
                f"<b>Parceiro:</b> {promo.parceiro}\n"
                f"<b>Pontuacao:</b> {promo.bonus_percentual} pts/real\n"
                f"<b>Detalhes:</b> {promo.descricao[:120]}\n\n"
                f'<a href="{promo.url}">Ver oferta</a>'
            )

    def enviar_alerta(self, promo: Promocao) -> bool:
        """Envia alerta de uma promoção para o Telegram com retry."""
        mensagem = self._formatar_mensagem(promo)
        payload = {
            "chat_id": self.chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                resp = requests.post(self.api_url, json=payload, timeout=10)
                resp.raise_for_status()
                logger.info(
                    "Alerta enviado: [%s] %s (%d%%)",
                    promo.tipo,
                    promo.parceiro,
                    promo.bonus_percentual,
                )
                return True
            except requests.RequestException as e:
                logger.warning(
                    "Tentativa %d/%d falhou ao enviar alerta: %s",
                    tentativa,
                    MAX_TENTATIVAS,
                    e,
                )
                if tentativa < MAX_TENTATIVAS:
                    time.sleep(2 * tentativa)

        logger.error("Falha ao enviar alerta após %d tentativas", MAX_TENTATIVAS)
        return False
