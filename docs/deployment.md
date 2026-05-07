# Production deployment

This deployment runs one Docker Compose stack from `/opt/offline-splitwise/backend`.

Public routes:

- `splitwise.ir`, `www.splitwise.ir` -> `landing`
- `api.splitwise.ir` -> `backend`
- `panel.splitwise.ir` -> `admin-panel`
- `pwa.splitwise.ir` -> `web`
- `webmail.splitwise.ir` -> `roundcube`
- `mail.splitwise.ir` -> SMTP/IMAP host

## Repositories

Use separate server clones:

```text
/opt/offline-splitwise/backend       splitwise-backend.git
/opt/offline-splitwise/landing       your separate landing repo
/opt/offline-splitwise/web           splitwise-web.git
```

`web-new-version` is no longer deployed. Copy its contents into `web`, commit them
to `splitwise-web/main`, then remove the old server clone if it exists.

## Server env

Copy `.env.production.example` to `/opt/offline-splitwise/backend/.env.production`
and fill real values. Runtime secrets belong only on the server.

Important context values:

```dotenv
BACKEND_CONTEXT=/opt/offline-splitwise/backend
LANDING_CONTEXT=/opt/offline-splitwise/landing
ADMIN_PANEL_CONTEXT=/opt/offline-splitwise/backend/admin-panel
WEB_CONTEXT=/opt/offline-splitwise/web
BACKEND_ENV_FILE=.env.production
```

GitHub only needs deploy access secrets:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_PORT`

Optional GitHub variables:

- `DEPLOY_ROOT=/opt/offline-splitwise/backend`
- `COMPOSE_ROOT=/opt/offline-splitwise/backend`
- `LANDING_DEPLOY_ROOT=/opt/offline-splitwise/landing`
- `WEB_DEPLOY_ROOT=/opt/offline-splitwise/web`
- `VITE_API_BASE_URL=https://api.splitwise.ir/api/v1`
- `VITE_PHONE_VERIFICATION_REQUIRED=false`
- `LANDING_ARTICLES_API_BASE_URL=https://api.splitwise.ir/api/v1`

## Mailserver

Copy `deploy/mailserver/mailserver.env.example` to
`deploy/mailserver/mailserver.env` and edit it for production.

Create mail accounts with:

```bash
docker compose --env-file .env.production exec mailserver setup email add user@splitwise.ir
docker compose --env-file .env.production exec mailserver setup alias add postmaster@splitwise.ir user@splitwise.ir
docker compose --env-file .env.production exec mailserver setup config dkim
```

After DKIM generation, publish the printed DNS TXT record.

## Backups

`postgres-backup` runs continuously and writes one custom-format `pg_dump` every
day to:

```text
/opt/offline-splitwise/backend/backups/postgres
```

Retention is controlled by `BACKUP_RETENTION_DAYS` in `.env.production`.

Restore example:

```bash
docker compose --env-file .env.production exec -T postgres createdb -U splitwise restored_db
docker compose --env-file .env.production exec -T postgres pg_restore -U splitwise -d restored_db /path/in/container.dump
```

For real restores, copy the dump into the postgres container or run `pg_restore`
from the host with a temporary postgres client.

## First deploy

```bash
cd /opt/offline-splitwise/backend
docker compose --env-file .env.production up -d --build postgres backend landing admin-panel web mailserver roundcube postgres-backup nginx
docker compose --env-file .env.production exec -T backend alembic upgrade head
```

Smoke checks:

```bash
curl -fsS https://api.splitwise.ir/health
curl -fsS https://api.splitwise.ir/api/v1/health
curl -I https://webmail.splitwise.ir
```
