from dataclasses import dataclass, field
import hashlib


@dataclass
class Promocao:
    """Representa uma promoção de transferência de pontos Livelo."""

    parceiro: str
    bonus_percentual: int
    data_inicio: str
    data_fim: str
    url: str
    promo_hash: str = field(init=False)

    def __post_init__(self):
        self.promo_hash = self._gerar_hash()

    def _gerar_hash(self) -> str:
        """Gera hash SHA-256 único para identificar a promoção.

        Combina parceiro + bônus + datas para garantir idempotência:
        mesma promoção nunca é processada duas vezes.
        """
        conteudo = f"{self.parceiro}|{self.bonus_percentual}|{self.data_inicio}|{self.data_fim}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()
