# Pay-Monopoly- (Wallet V1)

Monorepo du wallet Monopoly:

- `wallet-api`: FastAPI + PostgreSQL/SQLite, auth via FranceConnect mock, top-up Stripe, transfert P2P.
- `wallet-web`: Next.js App Router (`/login`, `/dashboard`).

## Prerequis

- Python 3.10+
- Node.js 18+
- PostgreSQL (optionnel en local si SQLite suffit)

## Wallet API

```powershell
cd "H:\Mon Drive\Pay-Monopoly-\wallet-api"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8007
```

### Endpoints principaux

- `POST /auth/session/sync`
- `GET /wallet/me`
- `POST /wallet/topups`
- `POST /wallet/transfers/p2p`
- `GET /wallet/transactions`
- `POST /wallet/webhooks/stripe`

## Wallet Web

```powershell
cd "H:\Mon Drive\Pay-Monopoly-\wallet-web"
copy .env.example .env.local
npm install
npm run dev
```

Ouvrir: `http://127.0.0.1:3002`

## Runbook integration locale

1. FranceConnect mock: `http://127.0.0.1:8001`
2. services-Monopoly: `http://127.0.0.1:8004`
3. stripe-Monopoly: `http://127.0.0.1:8006`
4. wallet-api: `http://127.0.0.1:8007`
5. wallet-web: `http://127.0.0.1:3002`

## Tests wallet-api

```powershell
cd "H:\Mon Drive\Pay-Monopoly-\wallet-api"
python -m pytest tests -v
```

