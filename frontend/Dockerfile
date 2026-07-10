# syntax=docker/dockerfile:1
# Placeholder static server until F5.1 introduces the Vite build stage.
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY public /usr/share/nginx/html

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -q -O- http://localhost:8080/ || exit 1
