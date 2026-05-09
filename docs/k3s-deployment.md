# k3s Deployment Runbook

این راهنما برای اجرای stack فعلی Splitwise روی یک سرور k3s تک‌نود نوشته شده است. فرض اصلی این است که مسیر production فعلی همچنان این است:

```bash
/opt/offline-splitwise/backend
```

در این مدل imageها روی خود سرور build می‌شوند و داخل containerd مربوط به k3s import می‌شوند. فعلا registry خارجی استفاده نمی‌شود.

## 1. نصب k3s و آماده‌سازی سرور

قبل از cutover مطمئن شو compose فعلی سالم است و backup دیتابیس داری:

```bash
cd /opt/offline-splitwise/backend
docker compose --env-file .env.production ps
mkdir -p backups/postgres
docker compose --env-file .env.production exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > backups/postgres/pre-k3s-$(date +%Y%m%d-%H%M%S).dump
```

k3s را نصب کن. Traefik را نگه می‌داریم تا Ingress روی پورت‌های 80/443 را مدیریت کند:

```bash
curl -sfL https://get.k3s.io | sh -
sudo systemctl status k3s
sudo kubectl get nodes
```

برای راحتی `kubectl` برای root/current user:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown "$(id -u):$(id -g)" ~/.kube/config
kubectl get nodes
```

دایرکتوری‌های hostPath را بساز:

```bash
sudo mkdir -p \
  /opt/offline-splitwise/k8s-data/postgres \
  /opt/offline-splitwise/k8s-data/files \
  /opt/offline-splitwise/k8s-data/mail/data \
  /opt/offline-splitwise/k8s-data/mail/state \
  /opt/offline-splitwise/k8s-data/mail/logs \
  /opt/offline-splitwise/k8s-data/roundcube \
  /opt/offline-splitwise/backend/backups/postgres
```

## 2. Namespace, Secretها و TLS

از root repo:

```bash
cd /opt/offline-splitwise/backend
kubectl apply -f deploy/k8s/namespace.yaml
```

secret runtime را با مقدارهای واقعی `.env.production` بساز. مقدارهای نمونه را کپی نکن:

```bash
kubectl -n splitwise create secret generic splitwise-runtime-secret \
  --from-literal=POSTGRES_DB='offline_splitwise' \
  --from-literal=POSTGRES_USER='splitwise' \
  --from-literal=POSTGRES_PASSWORD='<POSTGRES_PASSWORD>' \
  --from-literal=DATABASE_URL='postgresql+psycopg://splitwise:<POSTGRES_PASSWORD>@postgres:5432/offline_splitwise' \
  --from-literal=JWT_SECRET_KEY='<JWT_SECRET_KEY>' \
  --from-literal=ADMIN_PANEL_PASSWORD='<ADMIN_PANEL_PASSWORD>' \
  --from-literal=ADMIN_PANEL_PASSWORD_HASH='<ADMIN_PANEL_PASSWORD_HASH>' \
  --from-literal=ADMIN_PANEL_JWT_SECRET='<ADMIN_PANEL_JWT_SECRET>' \
  --from-literal=APP_DOWNLOAD_ADMIN_SECRET='<APP_DOWNLOAD_ADMIN_SECRET>' \
  --from-literal=SMS_IR_API_KEY='<SMS_IR_API_KEY>' \
  --from-literal=SMS_IR_VERIFY_TEMPLATE_ID='<SMS_IR_VERIFY_TEMPLATE_ID>' \
  --from-literal=SMS_IR_VERIFY_TEMPLATE_ID_ANDROID='<SMS_IR_VERIFY_TEMPLATE_ID_ANDROID>' \
  --from-literal=SMS_IR_INVITED_ACCOUNT_TEMPLATE_ID='<SMS_IR_INVITED_ACCOUNT_TEMPLATE_ID>'
```

اگر بعضی SMS valueها خالی هستند، همان empty string هم قابل قبول است. برای update:

```bash
kubectl -n splitwise delete secret splitwise-runtime-secret
# سپس دستور create بالا را دوباره اجرا کن
```

TLS secretها را از certificateهای فعلی بساز:

```bash
kubectl -n splitwise create secret tls splitwise-ir-tls \
  --cert deploy/nginx/certs/splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/splitwise.ir/privkey.pem

kubectl -n splitwise create secret tls api-splitwise-ir-tls \
  --cert deploy/nginx/certs/api.splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/api.splitwise.ir/privkey.pem

kubectl -n splitwise create secret tls panel-splitwise-ir-tls \
  --cert deploy/nginx/certs/panel.splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/panel.splitwise.ir/privkey.pem

kubectl -n splitwise create secret tls pwa-splitwise-ir-tls \
  --cert deploy/nginx/certs/pwa.splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/pwa.splitwise.ir/privkey.pem

kubectl -n splitwise create secret tls webmail-splitwise-ir-tls \
  --cert deploy/nginx/certs/webmail.splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/webmail.splitwise.ir/privkey.pem

kubectl -n splitwise create secret tls mail-splitwise-ir-tls \
  --cert deploy/nginx/certs/mail.splitwise.ir/fullchain.pem \
  --key deploy/nginx/certs/mail.splitwise.ir/privkey.pem
```

برای تمدید certificateها همین secretها را delete/create کن و بعد rollout restart بزن.

## 3. Build و import imageها داخل k3s

چون registry نداریم، هر image را با Docker build می‌کنیم و داخل containerd k3s import می‌کنیم:

```bash
cd /opt/offline-splitwise/backend

docker build -t splitwise/backend:local .
docker build -t splitwise/admin-panel:local ./admin-panel \
  --build-arg VITE_API_BASE_URL='https://api.splitwise.ir/api/v1' \
  --build-arg NPM_CONFIG_REGISTRY="${NPM_CONFIG_REGISTRY:-}"
docker build -t splitwise/landing:local ../landing \
  --build-arg VITE_API_BASE_URL='https://api.splitwise.ir/api/v1' \
  --build-arg LANDING_ARTICLES_API_BASE_URL='https://api.splitwise.ir/api/v1' \
  --build-arg VITE_SHOW_ENAMAD='true' \
  --build-arg NPM_CONFIG_REGISTRY="${NPM_CONFIG_REGISTRY:-}"
docker build -t splitwise/web:local ../web \
  --build-arg VITE_API_BASE_URL='https://api.splitwise.ir/api/v1' \
  --build-arg VITE_PHONE_VERIFICATION_REQUIRED='false' \
  --build-arg NPM_CONFIG_REGISTRY="${NPM_CONFIG_REGISTRY:-}"

docker save splitwise/backend:local -o /tmp/splitwise-backend.tar
docker save splitwise/admin-panel:local -o /tmp/splitwise-admin-panel.tar
docker save splitwise/landing:local -o /tmp/splitwise-landing.tar
docker save splitwise/web:local -o /tmp/splitwise-web.tar

sudo k3s ctr images import /tmp/splitwise-backend.tar
sudo k3s ctr images import /tmp/splitwise-admin-panel.tar
sudo k3s ctr images import /tmp/splitwise-landing.tar
sudo k3s ctr images import /tmp/splitwise-web.tar
```

بررسی imageها:

```bash
sudo k3s ctr images ls | grep splitwise
```

## 4. Deploy اولیه

اول config و سرویس‌های stateful را apply کن:

```bash
cd /opt/offline-splitwise/backend
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/postgres.yaml
kubectl -n splitwise rollout status statefulset/postgres
```

اگر دیتابیس فعلی compose را باید منتقل کنی، یک dump بگیر و داخل Postgres k3s restore کن:

```bash
docker compose --env-file .env.production exec -T postgres pg_dump -U splitwise -d offline_splitwise -Fc > /tmp/compose-postgres.dump

kubectl -n splitwise exec -i statefulset/postgres -- psql -U splitwise -d offline_splitwise \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

cat /tmp/compose-postgres.dump | kubectl -n splitwise exec -i statefulset/postgres -- \
  pg_restore -U splitwise -d offline_splitwise --no-owner --role=splitwise
```

migration را اجرا کن:

```bash
kubectl -n splitwise delete job backend-migration --ignore-not-found
kubectl apply -f deploy/k8s/backend-migration-job.yaml
kubectl -n splitwise wait --for=condition=complete job/backend-migration --timeout=180s
kubectl -n splitwise logs job/backend-migration
```

حالا appها، mail، backup و ingress:

```bash
kubectl apply -k deploy/k8s
kubectl -n splitwise rollout status deployment/backend
kubectl -n splitwise rollout status deployment/web
kubectl -n splitwise rollout status deployment/landing
kubectl -n splitwise rollout status deployment/admin-panel
kubectl -n splitwise rollout status deployment/mailserver
kubectl -n splitwise rollout status deployment/roundcube
```

قبل از cutover نهایی، compose را پایین بیاور تا پورت‌های 80/443 و mail آزاد شوند:

```bash
cd /opt/offline-splitwise/backend
docker compose --env-file .env.production down
kubectl apply -k deploy/k8s
```

## 5. عملیات روزانه

وضعیت کلی:

```bash
kubectl get nodes
kubectl -n splitwise get pods -o wide
kubectl -n splitwise get svc
kubectl -n splitwise get ingress
```

لاگ‌ها:

```bash
kubectl -n splitwise logs -f deployment/backend
kubectl -n splitwise logs -f deployment/web
kubectl -n splitwise logs -f deployment/mailserver
kubectl -n splitwise logs -f deployment/roundcube
```

restart بدون تغییر image:

```bash
kubectl -n splitwise rollout restart deployment/backend
kubectl -n splitwise rollout status deployment/backend
```

scale:

```bash
kubectl -n splitwise scale deployment/backend --replicas=3
kubectl -n splitwise scale deployment/web --replicas=2
```

تست self-healing:

```bash
kubectl -n splitwise get pods -l app=backend
kubectl -n splitwise delete pod -l app=backend --field-selector=status.phase=Running
kubectl -n splitwise get pods -l app=backend -w
```

rollback آخرین rollout:

```bash
kubectl -n splitwise rollout undo deployment/backend
kubectl -n splitwise rollout status deployment/backend
```

اجرای backup دستی:

```bash
kubectl -n splitwise create job --from=cronjob/postgres-backup postgres-backup-manual-$(date +%Y%m%d%H%M%S)
ls -lah /opt/offline-splitwise/backend/backups/postgres
```

## 6. Deploy نسخه جدید کد

روی سرور هر repo را pull کن:

```bash
cd /opt/offline-splitwise/backend && git pull
cd /opt/offline-splitwise/landing && git pull
cd /opt/offline-splitwise/web && git pull
```

imageهای تغییرکرده را rebuild/import کن. برای backend:

```bash
cd /opt/offline-splitwise/backend
docker build -t splitwise/backend:local .
docker save splitwise/backend:local -o /tmp/splitwise-backend.tar
sudo k3s ctr images import /tmp/splitwise-backend.tar

kubectl -n splitwise delete job backend-migration --ignore-not-found
kubectl apply -f deploy/k8s/backend-migration-job.yaml
kubectl -n splitwise wait --for=condition=complete job/backend-migration --timeout=180s

kubectl -n splitwise rollout restart deployment/backend
kubectl -n splitwise rollout status deployment/backend
```

برای PWA:

```bash
cd /opt/offline-splitwise/web
docker build -t splitwise/web:local \
  --build-arg VITE_API_BASE_URL='https://api.splitwise.ir/api/v1' \
  --build-arg VITE_PHONE_VERIFICATION_REQUIRED='false' \
  --build-arg NPM_CONFIG_REGISTRY="${NPM_CONFIG_REGISTRY:-}" .
docker save splitwise/web:local -o /tmp/splitwise-web.tar
sudo k3s ctr images import /tmp/splitwise-web.tar

kubectl -n splitwise rollout restart deployment/web
kubectl -n splitwise rollout status deployment/web
```

برای landing و admin-panel هم همین الگو را با imageهای `splitwise/landing:local` و `splitwise/admin-panel:local` اجرا کن.

## 7. Health checks

بعد از deploy:

```bash
curl -i https://api.splitwise.ir/health
curl -i https://api.splitwise.ir/api/v1/health
curl -I https://splitwise.ir
curl -I https://pwa.splitwise.ir
curl -I https://panel.splitwise.ir
curl -I https://webmail.splitwise.ir
```

Roundcube:

```bash
kubectl -n splitwise exec deployment/roundcube -- printenv | grep ROUNDCUBEMAIL
kubectl -n splitwise logs --tail=80 deployment/roundcube
kubectl -n splitwise logs --tail=80 deployment/mailserver
```

Mail DNS:

```bash
dig MX splitwise.ir +short
dig TXT splitwise.ir +short
dig TXT _dmarc.splitwise.ir +short
dig TXT mail._domainkey.splitwise.ir +short
dig A mail.splitwise.ir +short
```

## 8. نکات مهم

- چند replica روی یک سرور، خرابی pod/container را پوشش می‌دهد؛ اگر کل سرور down شود، کل k3s هم down است.
- Postgres و mailserver عمدا `replicas: 1` هستند. HA واقعی دیتابیس یا ایمیل نیاز به طراحی جداگانه دارد.
- قبل از cutover، compose nginx و mailserver نباید همزمان با k3s پورت‌های 80/443/25/587/993 را بگیرند.
- اگر secret یا configmap تغییر کرد، deployment مربوطه را restart کن:

```bash
kubectl -n splitwise rollout restart deployment/backend
kubectl -n splitwise rollout restart deployment/roundcube
kubectl -n splitwise rollout restart deployment/mailserver
```

