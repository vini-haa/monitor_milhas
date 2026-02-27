"""
Relatório analítico de promoções Livelo.

Gera estatísticas a partir do histórico salvo no PostgreSQL:
- Média de bônus por mês
- Parceiros mais frequentes
- Maior bônus registrado

Uso: python analysis.py
"""

import logging
import sys
from dotenv import load_dotenv
from src.config import Config
from src.database import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SQL_MEDIA_BONUS_POR_MES = """
SELECT
    TO_CHAR(criado_em, 'YYYY-MM') AS mes,
    ROUND(AVG(bonus_percentual), 1) AS media_bonus,
    COUNT(*) AS total_promocoes
FROM promocoes
GROUP BY mes
ORDER BY mes DESC;
"""

SQL_RANKING_PARCEIROS = """
SELECT
    parceiro,
    COUNT(*) AS total_promocoes,
    ROUND(AVG(bonus_percentual), 1) AS media_bonus,
    MAX(bonus_percentual) AS maior_bonus
FROM promocoes
GROUP BY parceiro
ORDER BY total_promocoes DESC
LIMIT 10;
"""

SQL_MAIOR_BONUS = """
SELECT parceiro, bonus_percentual, data_inicio, data_fim
FROM promocoes
ORDER BY bonus_percentual DESC
LIMIT 5;
"""

SQL_RESUMO_GERAL = """
SELECT
    COUNT(*) AS total,
    ROUND(AVG(bonus_percentual), 1) AS media_geral,
    MAX(bonus_percentual) AS maior,
    MIN(bonus_percentual) AS menor
FROM promocoes;
"""


def imprimir_separador(titulo: str):
    print(f"\n{'=' * 50}")
    print(f"  {titulo}")
    print(f"{'=' * 50}")


def relatorio_resumo(cursor):
    cursor.execute(SQL_RESUMO_GERAL)
    row = cursor.fetchone()
    if not row or row[0] == 0:
        print("\nNenhuma promoção registrada no banco ainda.")
        return False

    total, media, maior, menor = row
    imprimir_separador("RESUMO GERAL")
    print(f"  Total de promoções registradas: {total}")
    print(f"  Média geral de bônus:           {media}%")
    print(f"  Maior bônus registrado:         {maior}%")
    print(f"  Menor bônus registrado:         {menor}%")
    return True


def relatorio_media_mensal(cursor):
    cursor.execute(SQL_MEDIA_BONUS_POR_MES)
    rows = cursor.fetchall()
    if not rows:
        return

    imprimir_separador("MEDIA DE BONUS POR MES")
    print(f"  {'Mês':<12} {'Média Bônus':>12} {'Promoções':>12}")
    print(f"  {'-' * 12} {'-' * 12} {'-' * 12}")
    for mes, media, total in rows:
        print(f"  {mes:<12} {media:>11}% {total:>12}")


def relatorio_parceiros(cursor):
    cursor.execute(SQL_RANKING_PARCEIROS)
    rows = cursor.fetchall()
    if not rows:
        return

    imprimir_separador("RANKING DE PARCEIROS")
    print(f"  {'Parceiro':<20} {'Promos':>8} {'Média':>8} {'Maior':>8}")
    print(f"  {'-' * 20} {'-' * 8} {'-' * 8} {'-' * 8}")
    for parceiro, total, media, maior in rows:
        print(f"  {parceiro:<20} {total:>8} {media:>7}% {maior:>7}%")


def relatorio_top_bonus(cursor):
    cursor.execute(SQL_MAIOR_BONUS)
    rows = cursor.fetchall()
    if not rows:
        return

    imprimir_separador("TOP 5 MAIORES BONUS")
    for i, (parceiro, bonus, inicio, fim) in enumerate(rows, 1):
        print(f"  {i}. {parceiro} — {bonus}% (de {inicio} até {fim})")


def main():
    load_dotenv()
    config = Config()

    with DatabaseManager(config.database_url) as db:
        with db.conn.cursor() as cur:
            print("\n  RELATORIO DE PROMOCOES LIVELO")
            print(f"  {'=' * 46}")

            tem_dados = relatorio_resumo(cur)
            if not tem_dados:
                return

            relatorio_media_mensal(cur)
            relatorio_parceiros(cur)
            relatorio_top_bonus(cur)

    print(f"\n{'=' * 50}\n")


if __name__ == "__main__":
    main()
