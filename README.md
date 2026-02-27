# Monitor Milhas

Sistema automatizado de monitoramento de promoções de transferência de pontos **Livelo**. Detecta novas promoções com bônus para parceiros (Smiles, TudoAzul, Latam Pass, etc.), salva no PostgreSQL e envia alertas em tempo real via Telegram.

## Arquitetura

```
main.py → AppOrchestrator
              ├── LiveloScraper      (Playwright)  → extrai promoções do site
              ├── DatabaseManager    (psycopg2)    → persiste no PostgreSQL
              └── TelegramNotifier   (requests)    → envia alertas formatados
```

O sistema garante **idempotência**: cada promoção gera um hash SHA-256 único (parceiro + bônus + datas). Promoções já registradas são ignoradas — sem alertas duplicados.

## Estrutura do Projeto

```
monitor-milhas/
├── .github/workflows/monitor.yml   # Execução agendada (cron 6h)
├── src/
│   ├── config.py                    # Variáveis de ambiente
│   ├── models.py                    # Dataclass Promocao + hash
│   ├── scraper.py                   # Web scraper (Playwright)
│   ├── database.py                  # CRUD PostgreSQL + migration
│   ├── notifier.py                  # Telegram Bot API (HTML)
│   └── orchestrator.py              # Fluxo principal
├── main.py                          # Entry point
├── analysis.py                      # Relatório analítico
├── requirements.txt
└── .env.example
```

## Pré-requisitos

- Python 3.12+
- PostgreSQL (recomendado: [Neon.tech](https://neon.tech) — free tier)
- Bot do Telegram (criar via [@BotFather](https://t.me/BotFather))

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/monitor-milhas.git
cd monitor-milhas

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Instalar navegador headless
playwright install chromium
```

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

### Como obter cada variável

| Variável | Onde conseguir |
|----------|---------------|
| `DATABASE_URL` | [Neon.tech](https://neon.tech) → Dashboard → Connection string |
| `TELEGRAM_TOKEN` | Telegram → [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_CHAT_ID` | Envie uma mensagem para o bot e acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` |

## Uso

### Executar o monitor

```bash
python main.py
```

O script acessa a Livelo, extrai promoções ativas, salva as novas no banco e envia alertas no Telegram.

### Gerar relatório analítico

```bash
python analysis.py
```

Gera no terminal:
- Resumo geral (total, média, maior e menor bônus)
- Média de bônus por mês
- Ranking dos parceiros mais frequentes
- Top 5 maiores bônus registrados

## GitHub Actions

O workflow `.github/workflows/monitor.yml` executa o monitor automaticamente a cada **6 horas**.

Para ativar, configure os Secrets no repositório:

> **Settings → Secrets and variables → Actions → New repository secret**

Adicione: `DATABASE_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.

O workflow também aceita execução manual pela aba **Actions → Run workflow**.

## Schema do Banco

A tabela é criada automaticamente na primeira execução:

```sql
CREATE TABLE IF NOT EXISTS promocoes (
    id SERIAL PRIMARY KEY,
    parceiro VARCHAR(100) NOT NULL,
    bonus_percentual INTEGER NOT NULL,
    data_inicio VARCHAR(50),
    data_fim VARCHAR(50),
    url TEXT,
    promo_hash VARCHAR(64) UNIQUE NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
```

## Exemplo de Alerta no Telegram

```
Nova Promoção Livelo!

Parceiro: Smiles
Bônus: 80%
Período: 01/03 até 15/03

Ver promoção no site
```

## Tech Stack

- **Python 3.12** — linguagem principal
- **Playwright** — automação de browser headless
- **psycopg2** — driver PostgreSQL
- **PostgreSQL (Neon.tech)** — banco de dados serverless
- **Telegram Bot API** — notificações em tempo real
- **GitHub Actions** — orquestração e agendamento

## Licença

MIT
