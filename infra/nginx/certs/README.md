# infra/nginx/certs/

TLS certificates for the local/demo reverse proxy. **Never commit real certs or keys** — `*.crt`, `*.key`, `*.pem` are gitignored.

## Generate a dev self-signed cert

```bash
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout infra/nginx/certs/dev.key \
  -out infra/nginx/certs/dev.crt \
  -days 365 \
  -subj "/C=XX/O=Metro Intelligence Demo/CN=localhost"
```

The browser will warn about the self-signed cert — expected for local/demo use. Production deployments use the customer's PKI (see `docs/deployment-onpremise.md` and F11/F15).
