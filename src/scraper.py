import logging
import os
import re
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from src.models import Promocao

logger = logging.getLogger(__name__)

MELHORES_DESTINOS_URL = "https://www.melhoresdestinos.com.br/milhas"


class LiveloOfertasScraper:
    """Extrai ofertas de pontuação da página pública /ofertas da Livelo."""

    def __init__(self, url: str):
        self.url = url

    def extrair_promocoes(self) -> list[Promocao]:
        """Navega na página de ofertas e extrai os cards."""
        promocoes = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )

            try:
                logger.info("[Ofertas] Acessando %s", self.url)
                page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                # Scroll para carregar lazy content
                for i in range(8):
                    page.evaluate(f"window.scrollTo(0, {(i + 1) * 500})")
                    page.wait_for_timeout(1000)

                self._salvar_screenshot(page, "ofertas")

                # Estratégia 1: tenta extrair JSON embutido (SPAs React/Next.js)
                promocoes = self._extrair_via_json(page)

                # Estratégia 2: fallback via DOM
                if not promocoes:
                    logger.info("[Ofertas] JSON não encontrado, tentando via DOM")
                    promocoes = self._extrair_via_dom(page)

            except PlaywrightTimeout:
                logger.error("[Ofertas] Timeout ao carregar página")
                self._salvar_screenshot(page, "ofertas_timeout")
            except Exception as e:
                logger.error("[Ofertas] Erro inesperado: %s", e)
                self._salvar_screenshot(page, "ofertas_erro")
            finally:
                browser.close()

        logger.info("[Ofertas] Total extraídas: %d", len(promocoes))
        return promocoes

    def _extrair_via_json(self, page) -> list[Promocao]:
        """Extrai ofertas do __NEXT_DATA__ JSON embutido pela Livelo (Next.js)."""
        dados = page.evaluate("""() => {
            const nd = window.__NEXT_DATA__;
            if (!nd) return [];

            const comps = nd.props?.pageProps?.page?.components || [];
            const resultados = [];

            for (const comp of comps) {
                if (comp.type !== 'cbc_previsibility') continue;
                const children = comp.props?.card?.children || [];

                for (const child of children) {
                    const variations = child.status?.variations || [];
                    for (const v of variations) {
                        const titulo = v.title || '';
                        const descHtml = v.description || '';
                        // Remove tags HTML da descrição
                        const desc = descHtml.replace(/<[^>]+>/g, '').trim();
                        const imgAlt = v.image?.title || '';

                        // Extrai nome do parceiro do filename da imagem
                        let parceiro = '';
                        if (imgAlt) {
                            // Remove extensão, prefixos numéricos e sufixos de data
                            let nome = imgAlt
                                .replace(/\\.(webp|png|jpg|jpeg|svg)$/i, '')
                                .replace(/^\\d{6,}-\\d+-/, '')          // "25022026-183-"
                                .replace(/--?\\d{6}.*$/, '')            // "--260226"
                                .replace(/-\\d{6}.*$/, '')              // "-260226"
                                .replace(/\\d{2,4}x\\d{2,4}[-_]?/g, '') // "360x160"
                                .replace(/[-_]?(vitrine|previsibilidade|previsibilidade|site|web|webp|bra|1x|2x)[-_]?/gi, ' ')
                                .replace(/[0-9a-f]{8}-[0-9a-f]{4}/gi, '') // UUIDs
                                .replace(/[-_]+/g, ' ')
                                .replace(/\\s+/g, ' ')
                                .trim();

                            // Remove "p" solto no início (resto de "webp")
                            nome = nome.replace(/^p\\s+/i, '');
                            // Remove parênteses com números "(58)"
                            nome = nome.replace(/\\(\\d+\\)/g, '').trim();
                            if (nome.length >= 2 && nome.length <= 40 && !/^\\d+$/.test(nome)) {
                                parceiro = nome.replace(/\\b\\w/g, c => c.toUpperCase());
                            }
                        }

                        // Fallback: extrai nome do título
                        if (!parceiro || parceiro.length < 3) {
                            const textoT = titulo;
                            // "Ganhe 5 pontos por real em produtos da Polishop" -> "Polishop"
                            const emMatch = textoT.match(/(?:da|do|no|na|com\\s+(?:o|a)?)\\s+([A-Z][\\w\\s]{2,25})/);
                            if (emMatch) {
                                parceiro = emMatch[1].trim();
                            } else {
                                // "Samsung Galaxy S26: 10 pontos por real" -> "Samsung Galaxy S26"
                                const tMatch = textoT.match(/^(.+?)[:!]?\\s*\\d+\\s*pontos/i);
                                if (tMatch) {
                                    parceiro = tMatch[1]
                                        .replace(/^(ganhe|compre|fa.a|use|contrate)\\s+(o|a|no|na|em|at.|seus?)?\\s*/i, '')
                                        .trim();
                                }
                            }
                        }

                        if (!parceiro || parceiro.length < 3) {
                            // Último fallback: usa o título completo resumido
                            parceiro = titulo.substring(0, 50);
                        }

                        // Filtro: descarta nomes claramente ruins
                        if (/^(ganhe|compre|tê|sam|fa.a|use|\\(\\d)$/i.test(parceiro.trim())) {
                            // Tenta extrair do título com padrão mais agressivo
                            const palavras = titulo.split(/\\s+/).filter(p =>
                                p.length > 2 && /^[A-Z]/.test(p) && !/^(Ganhe|Compre|Nos|Para|Leve)$/.test(p));
                            if (palavras.length > 0) parceiro = palavras.join(' ').substring(0, 40);
                            else parceiro = titulo.substring(0, 50);
                        }

                        // Limpeza final de nomes conhecidos
                        const nomesMapa = {
                            'Magalu': 'Magalu', 'Casasbahia': 'Casas Bahia',
                            'Carrefourmercado': 'Carrefour', 'Polishop': 'Polishop',
                            'Lojascolombo': 'Lojas Colombo', 'Webcontinentalmarketplace': 'Webcontinental',
                            'Beto Carrero': 'Beto Carrero World', 'Liga Vitoria': 'Liga Vitória',
                            'Klubi Auto': 'Klubi Auto', 'Klubi Celular': 'Klubi Celular',
                            'Klubi Viagem': 'Klubi Viagem', 'Tokio Marine': 'Tokio Marine',
                            'Universal Assistance': 'Universal Assistance',
                            'Mycon': 'Mycon', 'Hero': 'Hero', 'Astropay': 'AstroPay',
                            'Rico': 'Rico', 'C6': 'C6 Bank', 'Assist Card': 'Assist Card',
                            'Sulamerica': 'SulAmérica', 'Seguro Viagem': 'Bradesco Seguro Viagem',
                            'Continentalmarketplace': 'Webcontinental',
                            'Webcontinentalmarketplace': 'Webcontinental',
                        };
                        for (const [chave, valor] of Object.entries(nomesMapa)) {
                            if (parceiro.toLowerCase().includes(chave.toLowerCase())) {
                                parceiro = valor;
                                break;
                            }
                        }

                        // Extrai pontos do título ou descrição
                        const textoCompleto = titulo + ' ' + desc;
                        const ptMatch = textoCompleto.match(/(\\d+)\\s*pontos?\\s*por\\s*real/i);
                        const pontos = ptMatch ? parseInt(ptMatch[1]) : 0;

                        // Extrai datas da descrição
                        const datasMatch = desc.match(/\\d{2}\\/\\d{2}(?:\\/\\d{2,4})?/g) || [];

                        if (titulo) {
                            resultados.push({
                                parceiro: parceiro,
                                pontos: pontos,
                                titulo: titulo,
                                descricao: desc.substring(0, 150),
                                dataInicio: datasMatch[0] || 'N/A',
                                dataFim: datasMatch[1] || datasMatch[0] || 'N/A',
                            });
                        }
                    }
                }
            }
            return resultados;
        }""")

        if not dados:
            return []

        promocoes = []
        for d in dados:
            pontos = d["pontos"]
            if pontos < 1 or pontos > 100:
                continue

            promo = Promocao(
                parceiro=d["parceiro"],
                bonus_percentual=pontos,
                data_inicio=d["dataInicio"],
                data_fim=d["dataFim"],
                url=self.url,
                tipo="oferta",
                descricao=f'{d["titulo"]} — {d["descricao"]}',
            )
            promocoes.append(promo)
            logger.info("[Ofertas] %s — %d pts/real", d["parceiro"], pontos)

        return promocoes

    def _extrair_via_dom(self, page) -> list[Promocao]:
        """Encontra ofertas via JavaScript navegando o DOM."""
        dados = page.evaluate("""() => {
            const resultados = [];
            const walker = document.createTreeWalker(
                document.body, NodeFilter.SHOW_TEXT, null
            );
            while (walker.nextNode()) {
                const texto = walker.currentNode.textContent.trim();
                const match = texto.match(/(\\d+)\\s*pontos?\\s*por\\s*real/i);
                if (!match) continue;

                const pontos = parseInt(match[1]);
                if (pontos < 1 || pontos > 100) continue;

                // Sobe até achar o card container (máx 10 níveis)
                let card = walker.currentNode.parentElement;
                for (let i = 0; i < 10; i++) {
                    if (!card || !card.parentElement) break;
                    const rect = card.getBoundingClientRect();
                    if (rect.height > 100 && rect.width > 150) break;
                    card = card.parentElement;
                }
                if (!card) continue;

                let parceiro = '';

                // 1. Tenta extrair o nome da loja da URL do link
                const links = card.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    // URLs como /ofertas/magalu ou /ofertas/casas-bahia
                    const urlMatch = href.match(/\\/ofertas\\/([a-z0-9-]+)/i);
                    if (urlMatch) {
                        parceiro = urlMatch[1]
                            .replace(/-/g, ' ')
                            .replace(/\\b\\w/g, c => c.toUpperCase());
                        break;
                    }
                }

                // 2. Tenta via img alt text
                if (!parceiro) {
                    const imgs = card.querySelectorAll('img[alt]');
                    for (const img of imgs) {
                        const alt = (img.getAttribute('alt') || '').trim();
                        if (alt && alt.length > 1 && alt.length < 40
                            && !alt.includes('.svg') && !alt.includes('.png')
                            && !alt.toLowerCase().includes('logo livelo')
                            && !alt.toLowerCase().includes('banner')
                            && !alt.toLowerCase().includes('imagem clicável')) {
                            parceiro = alt;
                            break;
                        }
                    }
                }

                // 3. Fallback: primeiro texto legível no card
                if (!parceiro) {
                    const textos = card.innerText.split('\\n')
                        .map(l => l.trim())
                        .filter(l => l.length >= 3 && l.length <= 60
                            && !l.match(/^\\d+\\s*pontos/i)
                            && !l.match(/^por\\s*real/i)
                            && !l.match(/^(compre e pontue|ver regra|eu quero)$/i));
                    if (textos.length > 0) {
                        parceiro = textos[0];
                    }
                }

                if (!parceiro) continue;

                // Pega o melhor link disponível
                let href = '';
                for (const link of links) {
                    const h = link.getAttribute('href') || '';
                    if (h.includes('/ofertas/')) { href = h; break; }
                    if (!href && h) href = h;
                }

                // Texto completo do card para descrição
                const descricao = card.innerText.substring(0, 150)
                    .split('\\n').filter(l => l.trim()).slice(0, 3).join(' | ');

                resultados.push({
                    parceiro: parceiro,
                    pontos: pontos,
                    href: href,
                    descricao: descricao
                });
            }

            // Remove duplicados pelo parceiro+pontos
            const vistos = new Set();
            return resultados.filter(r => {
                const chave = r.parceiro + '|' + r.pontos;
                if (vistos.has(chave)) return false;
                vistos.add(chave);
                return true;
            });
        }""")

        promocoes = []
        for d in dados:
            href = d["href"] or self.url
            if href and not href.startswith("http"):
                href = f"https://www.livelo.com.br{href}"

            promo = Promocao(
                parceiro=d["parceiro"],
                bonus_percentual=d["pontos"],
                data_inicio="N/A",
                data_fim="N/A",
                url=href,
                tipo="oferta",
                descricao=d["descricao"],
            )
            promocoes.append(promo)
            logger.info("[Ofertas] %s — %d pts/real", d["parceiro"], d["pontos"])

        return promocoes

    @staticmethod
    def _salvar_screenshot(page, prefixo: str):
        try:
            os.makedirs("screenshots", exist_ok=True)
            caminho = f"screenshots/{prefixo}_debug.png"
            page.screenshot(path=caminho, full_page=True)
            logger.info("Screenshot salvo em: %s", caminho)
        except Exception as e:
            logger.warning("Não foi possível salvar screenshot: %s", e)


class BlogTransferenciaScraper:
    """Extrai promoções de bônus de transferência do blog Melhores Destinos."""

    def __init__(self):
        self.url = MELHORES_DESTINOS_URL

    def extrair_promocoes(self) -> list[Promocao]:
        """Busca posts recentes sobre bônus de transferência de pontos."""
        promocoes = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )

            try:
                logger.info("[Blog] Acessando %s", self.url)
                page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                self._salvar_screenshot(page, "blog")

                # Busca links de artigos sobre milhas/bônus
                artigos = page.query_selector_all("article a, .post a, h2 a, h3 a")
                logger.info("[Blog] Encontrados %d links de artigos", len(artigos))

                urls_vistos = set()
                for artigo in artigos:
                    try:
                        href = artigo.get_attribute("href") or ""
                        titulo = artigo.inner_text().strip()

                        if not titulo or not href or href in urls_vistos:
                            continue
                        urls_vistos.add(href)

                        promo = self._analisar_titulo(titulo, href)
                        if promo:
                            promocoes.append(promo)
                    except Exception as e:
                        logger.warning("[Blog] Erro ao processar artigo: %s", e)

            except PlaywrightTimeout:
                logger.error("[Blog] Timeout ao carregar página")
            except Exception as e:
                logger.error("[Blog] Erro inesperado: %s", e)
            finally:
                browser.close()

        logger.info("[Blog] Total extraídas: %d", len(promocoes))
        return promocoes

    def _analisar_titulo(self, titulo: str, url: str) -> Promocao | None:
        """Analisa o título do post para extrair dados de promoção."""
        titulo_lower = titulo.lower()

        # Filtra apenas posts sobre bônus/transferência
        palavras_chave = ["bônus", "bonus", "transferência", "transferencia", "milhas"]
        if not any(p in titulo_lower for p in palavras_chave):
            return None

        # Extrai percentual de bônus
        match_bonus = re.search(r"(\d+)\s*%", titulo)
        if not match_bonus:
            return None
        bonus = int(match_bonus.group(1))
        if bonus <= 0 or bonus > 200:
            return None

        # Identifica o programa/parceiro
        programas = {
            "smiles": "Smiles",
            "azul": "Azul Fidelidade",
            "tudoazul": "TudoAzul",
            "latam": "LATAM Pass",
            "all accor": "All Accor",
            "accor": "All Accor",
            "tap": "TAP Miles&Go",
            "united": "United MileagePlus",
            "emirates": "Emirates Skywards",
            "iberia": "Iberia Plus",
            "american": "AAdvantage",
            "flying blue": "Flying Blue",
            "avianca": "Avianca",
            "livelo": "Livelo",
            "esfera": "Esfera",
        }

        parceiro = None
        for chave, nome in programas.items():
            if chave in titulo_lower:
                parceiro = nome
                break

        if not parceiro:
            parceiro = titulo[:50]

        # Extrai datas se houver
        datas = re.findall(r"\d{2}/\d{2}(?:/\d{2,4})?", titulo)
        data_inicio = datas[0] if datas else "N/A"
        data_fim = datas[1] if len(datas) >= 2 else "N/A"

        logger.info("[Blog] Encontrado: %s %d%% - %s", parceiro, bonus, titulo[:60])

        return Promocao(
            parceiro=parceiro,
            bonus_percentual=bonus,
            data_inicio=data_inicio,
            data_fim=data_fim,
            url=url,
            tipo="transferencia",
            descricao=titulo,
        )

    @staticmethod
    def _salvar_screenshot(page, prefixo: str):
        try:
            os.makedirs("screenshots", exist_ok=True)
            caminho = f"screenshots/{prefixo}_debug.png"
            page.screenshot(path=caminho, full_page=True)
            logger.info("Screenshot salvo em: %s", caminho)
        except Exception as e:
            logger.warning("Não foi possível salvar screenshot: %s", e)
