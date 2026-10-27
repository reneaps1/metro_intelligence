# Two editions on the VPS — runbook (IQ-F9)

One codebase, two deployments from the same commit:

| | Metrology (current) | Industrial (demo) |
|---|---|---|
| Compose project | `metro-intelligence` | `metro-intelligence-industrial` |
| Env file on the VPS | `.env` | `.env.industrial` |
| `APP_EDITION` | `metrology` | `industrial` |
| `INSTANCE` | `metro` (default) | e.g. `metro-industrial` |
| Volumes | `metro_pgdata`, `metro_minio_data` | `<INSTANCE>_pgdata`, `<INSTANCE>_minio_data` |
| Data network (internal) | `metro_net_data` | `<INSTANCE>_net_data` |
| Traefik routers | `metro-api`, `metro-web` | `<INSTANCE>-api`, `<INSTANCE>-web` |
| Public host | `metro.onkaizen.com.mx` | `PUBLIC_HOST` (e.g. `industrial.<domain>`) |

Both share only `metro_net_app`, the network Traefik uses to reach the frontends
and APIs. Each edition has its own PostgreSQL and MinIO on its own internal
network: the industrial demo never touches metrology data. With no new
variables set, `docker-compose.vps.yml` renders exactly the names the metrology
deployment already uses (checked by `tests/deploy/test_vps_compose.py`).

Every change on the VPS, in GitHub secrets or in DNS needs the owner's explicit
authorization (plan, F9).

## 0. Why the current deploy fails

The deploy runs of 2026-10-13 failed in 0.2 s with
`dial tcp: lookup *** on …:53: no such host`: the **`VPS_HOST` secret does not
resolve** (wrong hostname, or extra characters such as `https://`, a path, a
port or a trailing space). The code and the VPS were never reached. Fix: set
`VPS_HOST` to the bare hostname or IP of the VPS. The workflow now checks this
first and fails with an explicit message, without printing the secret.

## 1. Capacity check (before adding the second edition)

The industrial edition adds a PostgreSQL, a MinIO, a backend and a frontend.

```bash
free -h && df -h /var/lib/docker && docker stats --no-stream
```

Rule of thumb: ~1.5 GB of free RAM for the second stack. If it is short, an
alternative is one PostgreSQL with two databases (not implemented; needs a
compose change and a decision).

## 2. One-time setup of the industrial edition (on the VPS)

```bash
cd /home/rene/projects/metro_intelligence

# a) Shared proxy network (already exists if metrology is running)
docker network inspect metro_net_app >/dev/null || docker network create metro_net_app

# b) Private demo files, outside the repo and the images
mkdir -p ~/metro-private && chmod 700 ~/metro-private
#    copy report-summary.json and model-lab.json from the local demo-private/ (scp)

# c) Env file (never in the repo)
cp .env.example .env.industrial && chmod 600 .env.industrial
#    edit: see the "VPS editions" block at the end of .env.example. At least
#    APP_EDITION=industrial, INSTANCE, PUBLIC_HOST, APP_ENV_FILE=.env.industrial,
#    its own POSTGRES_* / MINIO_* / JWT_SECRET / APP_SECRET_KEY,
#    DEMO_PRIVATE_DIR=/home/<user>/metro-private (absolute: compose does not expand ~),
#    DEMO_REPORT_SUMMARY_PATH=/run/demo-private/report-summary.json,
#    DEMO_MODEL_LAB_PATH=/run/demo-private/model-lab.json,
#    DEMO_CLIENT_LABEL and DEMO_CRITICAL_NEST (values in the private brief),
#    SEED_DEMO_USER_PASSWORD (APP_ENV other than production creates the
#    fictitious admin luis.torres@demo.local at startup).

# d) Dry run, then deploy
docker compose -p metro-intelligence-industrial --env-file .env.industrial -f docker-compose.vps.yml config --quiet
bash scripts/deploy_edition.sh industrial
```

e) DNS: an A/AAAA record for `PUBLIC_HOST` pointing to the VPS. Traefik's
`letsencrypt` resolver issues the certificate on the first request once DNS
resolves.

The first deploy of this compose file also re-renders the **metrology** stack
(same names, `net_app` now declared `external`). Dry run it first:

```bash
docker compose -p metro-intelligence --env-file .env -f docker-compose.vps.yml config --quiet
```

## 3. Updating

- Merge to `main` → the `Deploy Metro Intelligence` workflow resets the VPS
  checkout to `origin/main` and runs `scripts/deploy_edition.sh` for
  `metrology` and `industrial` (the latter is skipped while `.env.industrial`
  does not exist).
- Before a demo, redeploy only one edition: *Actions → Deploy Metro
  Intelligence → Run workflow → editions = industrial*.

`scripts/deploy_edition.sh` refuses an env file whose `APP_EDITION` does not
match, validates the compose file, builds, starts, then waits for `/health`
inside the backend container and checks the running edition.

## 4. Smoke test

- Script output: `OK <edition> deployed and healthy`.
- Browser: `https://<PUBLIC_HOST>` → log in → the **Demo industrial** menu
  exists; `https://metro.onkaizen.com.mx` → no demo menu, demo routes redirect.
- Logs: `docker compose -p <project> --env-file <env> -f docker-compose.vps.yml logs backend --tail 50`
  (an invalid private file shows a warning and the illustrative placeholder,
  never the path or its content).

## 5. Rolling back

- Code: `git reset --hard <previous-sha>` in the VPS checkout, then
  `bash scripts/deploy_edition.sh <edition>`; or revert the commit on `main`
  and let the workflow redeploy. Volumes are not touched.
- Remove the industrial edition entirely:
  `docker compose -p metro-intelligence-industrial --env-file .env.industrial -f docker-compose.vps.yml down`
  (add `-v` only to also delete its database and object storage — irreversible),
  then delete the DNS record and `.env.industrial`.

## 6. Rules

- Real customer CSVs are never uploaded to the public VPS without the
  customer's explicit authorization; the demo runs on fictitious and private
  summary data.
- `.env*` files and `~/metro-private` stay on the VPS, mode 600/700.
- Secrets differ between editions.
