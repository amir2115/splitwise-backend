# Nginx certificates

The compose stack expects certificates at:

- `deploy/nginx/certs/splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/splitwise.ir/privkey.pem`
- `deploy/nginx/certs/api.splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/api.splitwise.ir/privkey.pem`
- `deploy/nginx/certs/panel.splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/panel.splitwise.ir/privkey.pem`
- `deploy/nginx/certs/pwa.splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/pwa.splitwise.ir/privkey.pem`
- `deploy/nginx/certs/webmail.splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/webmail.splitwise.ir/privkey.pem`
- `deploy/nginx/certs/mail.splitwise.ir/fullchain.pem`
- `deploy/nginx/certs/mail.splitwise.ir/privkey.pem`

For the first server boot, create these certificates with certbot on the host or mount
your existing certificate directories into the paths above. The ACME challenge webroot
is mounted at `deploy/nginx/acme`.
