# 🍖 Greazy — Restaurant Ordering App

A Flask restaurant ordering app: customer menu + cart + checkout, user
accounts, and a live admin dashboard for managing incoming orders.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env       # then edit .env — see below
python app.py
```

Open:
- Customer app: http://localhost:5000
- Staff dashboard: http://localhost:5000/staff (admin login required)

## Before you deploy this anywhere public

The `.env.example` file lists everything, but the two that matter most:

1. **`FLASK_SECRET_KEY`** — generate a real one:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Sessions (including admin sessions) are cryptographically signed with
   this key. If it's ever left as a hardcoded default, anyone with the
   source can forge a login.

2. **`ADMIN_PASSWORD`** — set this to something other than the default
   before you go live. It's used to seed the admin account the first
   time the app creates its database.

Also set `FLASK_ENV=production` when deploying — this turns off Flask's
interactive debugger (which otherwise allows arbitrary code execution if
exposed publicly) and marks the session cookie HTTPS-only.

## What's in here

```
greazy-app/
├── app.py              # Flask app: routes, API, DB setup
├── requirements.txt
├── .env.example         # copy to .env and fill in
├── .gitignore
├── templates/
│   ├── index.html      # customer menu, cart, checkout
│   ├── login.html
│   ├── register.html
│   └── staff.html       # admin dashboard
└── data/                 # SQLite DB is created here on first run
```

## Default admin login

Seeded on first run, from your `.env`:
- Email: value of `ADMIN_EMAIL` (default `admin@greazy.co.za`)
- Password: value of `ADMIN_PASSWORD` (default `admin123` — change this)

## How pricing works (security note)

Order totals are calculated **server-side** in `app.py` from the fixed
menu (`MENU_ITEMS`), not from whatever the browser sends. The client's
cart only tells the server *which items and quantities* were selected —
the price for each is always looked up from the server's own menu data.
This closes off the classic "edit the request in dev tools to pay less"
attack.

## Email notifications

If `SMTP_USER` / `SMTP_PASSWORD` aren't set, the app just prints new
order details to the console instead of emailing — handy for local dev.
To enable real emails (Gmail example):

1. Enable 2FA on the Gmail account.
2. Create an [app password](https://myaccount.google.com/apppasswords).
3. Set `SMTP_USER` and `SMTP_PASSWORD` in `.env` to that email/app password.

For SendGrid, Mailgun, or SES, just point `SMTP_SERVER` at their SMTP
endpoint and use their credentials instead.

## API overview

| Route | Method | Notes |
|---|---|---|
| `/register` | POST | Create account, auto-login |
| `/login` | POST | Session login |
| `/logout` | GET | Clears session |
| `/api/menu` | GET | Menu items |
| `/api/payment-methods` | GET | Available payment options |
| `/api/orders` | GET/POST | List your orders / place an order (login required) |
| `/api/admin/orders` | GET | All orders (admin only) |
| `/api/orders/<id>/status` | PUT | Update order status (admin only) |
| `/api/orders/<id>/payment` | PUT | Update payment status (admin only) |

## Deploying

**Gunicorn (any VPS):**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Set your real environment variables (not the `.env` file — use your
host's secret manager) when deploying.

## Resetting the database

```bash
rm data/greazy.db
python app.py   # recreates it and reseeds the admin account
```
