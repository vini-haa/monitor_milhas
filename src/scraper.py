import logging
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from src.models import Promocao

logger = logging.getLogger(__name__)


class LiveloScraper:
    """Extrai promoções de transferência com bônus do site da Livelo."""

    def __init__(self, url: str):
        self.url = url

    def extrair_promocoes(self) -> list[Promocao]:
        """Navega até a página da Livelo e extrai as promoções ativas."""
        promocoes = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                logger.info("Acessando %s", self.url)
                page.goto(self.url, wait_until="networkidle", timeout=60000)

                # Aguarda os cards de promoções carregarem
                page.wait_for_selector(
                    "[class*='card'], [class*='partner'], [class*='promotion']",
                    timeout=15000,
                )

                # Extrai os cards de parceiros com bônus de transferência
                cards = page.query_selector_all(
                    "[class*='card'], [class*='partner'], [class*='promotion']"
                )
                logger.info("Encontrados %d cards na página", len(cards))

                for card in cards:
                    try:
                        promo = self._extrair_card(card)
                        if promo:
                            promocoes.append(promo)
                    except Exception as e:
                        logger.warning("Erro ao extrair card: %s", e)
                        continue

            except PlaywrightTimeout:
                logger.error("Timeout ao carregar a página da Livelo")
                self._salvar_screenshot(page, "timeout")
            except Exception as e:
                logger.error("Erro inesperado no scraper: %s", e)
                self._salvar_screenshot(page, "erro")
            finally:
                browser.close()

        logger.info("Total de promoções extraídas: %d", len(promocoes))
        return promocoes

    def _extrair_card(self, card) -> Promocao | None:
        """Extrai dados de um card individual de promoção."""
        texto = card.inner_text()
        if not texto.strip():
            return None

        # Tenta extrair o nome do parceiro
        parceiro_el = card.query_selector(
            "[class*='name'], [class*='title'], [class*='partner'], h3, h4, strong"
        )
        parceiro = parceiro_el.inner_text().strip() if parceiro_el else None

        # Tenta extrair o percentual de bônus
        bonus = self._extrair_bonus(texto)

        # Tenta extrair datas
        data_inicio, data_fim = self._extrair_datas(texto)

        # Tenta extrair link
        link_el = card.query_selector("a[href]")
        url = link_el.get_attribute("href") if link_el else self.url

        if not url.startswith("http"):
            url = f"https://www.livelo.com.br{url}"

        if parceiro and bonus and bonus > 0:
            return Promocao(
                parceiro=parceiro,
                bonus_percentual=bonus,
                data_inicio=data_inicio or "N/A",
                data_fim=data_fim or "N/A",
                url=url,
            )
        return None

    @staticmethod
    def _extrair_bonus(texto: str) -> int | None:
        """Extrai percentual de bônus do texto (ex: '80%', 'bônus de 100%')."""
        import re

        match = re.search(r"(\d+)\s*%", texto)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extrair_datas(texto: str) -> tuple[str | None, str | None]:
        """Extrai datas de início e fim do texto do card."""
        import re

        # Padrão: dd/mm/yyyy ou dd/mm
        datas = re.findall(r"\d{2}/\d{2}(?:/\d{4})?", texto)
        if len(datas) >= 2:
            return datas[0], datas[1]
        elif len(datas) == 1:
            return datas[0], None
        return None, None

    @staticmethod
    def _salvar_screenshot(page, prefixo: str):
        """Salva screenshot da página para debug."""
        try:
            os.makedirs("screenshots", exist_ok=True)
            caminho = f"screenshots/{prefixo}_debug.png"
            page.screenshot(path=caminho, full_page=True)
            logger.info("Screenshot salvo em: %s", caminho)
        except Exception as e:
            logger.warning("Não foi possível salvar screenshot: %s", e)
