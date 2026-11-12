# Livelo Points Monitor

Automated monitoring system for **Livelo** (Brazilian loyalty program) point-transfer promotions. It scrapes two sources, detects new bonus offers to airline partners (Smiles, TudoAzul, Latam Pass), stores them in PostgreSQL, and sends real-time Telegram alerts — running unattended on GitHub Actions since early 2025.

**Why it exists:** transfer bonuses of 80–100% appear with no warning and expire in days. Catching them manually means checking the site every morning. This bot does it for me and pings my phone within hours of a new offer.

## Architecture

```
main.py → AppOrchestrator
              ├── LiveloScraper      (Playwright)  → scrapes offers page + blog
              ├── DatabaseManager    (psycopg2)    → persists to PostgreSQL (Neon)
              └── TelegramNotifier   (requests)    → sends formatted alerts
```

Key design decisions:

- **Idempotency by content hash** — each promotion generates a unique SHA-256 hash (partner + bonus + dates). Already-seen promotions are skipped: no duplicate alerts, safe to re-run anytime.
- **Dual-source scraping** — the offers page and the Livelo blog are scraped independently; either one failing doesn't block the other.
- **Zero-cost infrastructure** — GitHub Actions cron (every 6h) + Neon PostgreSQL free tier + Telegram Bot API. No server to maintain.

## Project structure

```
monitor-milhas/
├── .github/workflows/monitor.yml   # Scheduled run (cron, every 6h)
├── src/
│   ├── config.py                    # Environment variables
│   ├── models.py                    # Promotion dataclass + hashing
│   ├── scraper.py                   # Playwright web scraper
│   ├── database.py                  # PostgreSQL CRUD + migration
│   ├── notifier.py                  # Telegram Bot API (HTML messages)
│   └── orchestrator.py              # Main flow
├── main.py                          # Entry point
├── analysis.py                      # Analytics report over collected data
└── requirements.txt
```

## Example alert

```
New Livelo promotion!

Partner: Smiles
Bonus: 80%
Period: Mar 01 – Mar 15

→ View offer
```

## Setup

Requirements: Python 3.12+, a PostgreSQL instance (Neon free tier works), and a Telegram bot token from [@BotFather](https://t.me/BotFather).

```bash
git clone https://github.com/vini-haa/monitor_milhas.git
cd monitor_milhas
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # fill in DB and Telegram credentials
python main.py
```

The database table is created automatically on first run:

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

## Tech stack

Python 3.12 · Playwright · PostgreSQL (Neon) · psycopg2 · Telegram Bot API · GitHub Actions

## License

MIT
