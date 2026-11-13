# syntax=docker/dockerfile:1
# Frontend estático servido por nginx sin privilegios; /api se reenvía al contenedor de la API.

FROM node:26.13.0-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31.7-alpine AS runtime
# Parches de seguridad de Alpine publicados después de la imagen base.
USER root
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
# La imagen base ya usa el usuario sin privilegios 101 (nginx); se declara explícitamente.
USER 101
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
