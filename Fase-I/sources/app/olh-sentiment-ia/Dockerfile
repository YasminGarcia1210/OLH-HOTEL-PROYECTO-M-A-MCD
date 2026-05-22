# Sin directiva `# syntax=docker/dockerfile:1`: en Podman (Windows) el frontend
# BuildKit puede tardar o parecer colgado al pull desde Docker Hub.
#
# Build context: la propia carpeta de la app `sources/app/olh-sentiment-ia`.
# Usá SIEMPRE --ignorefile con context.dockerignore para no enviar `.next/`
# y `node_modules/` locales (cientos de MB → la consola queda muda al
# transferir el tar a Podman Machine).
#
# Las variables NEXT_PUBLIC_* en Next.js se inyectan en BUILD TIME al bundle
# del cliente. Por eso van como ARG/ENV aquí: cualquier cambio de URL implica
# rebuild + push de imagen nueva.
#
#   podman build `
#     --ignorefile sources/app/olh-sentiment-ia/context.dockerignore `
#     --build-arg NEXT_PUBLIC_DASHBOARD_API_URL=https://... `
#     --build-arg NEXT_PUBLIC_DASHBOARD_HOTEL_ID=1 `
#     --build-arg NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=https://... `
#     -f sources/app/olh-sentiment-ia/Dockerfile `
#     -t <tag> sources/app/olh-sentiment-ia

############################
# Stage 1: instalar deps
############################
FROM node:22-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

############################
# Stage 2: build (Next.js)
############################
FROM node:22-alpine AS builder
WORKDIR /app

# Recibe las URLs públicas: deben fijarse aquí o el bundle del cliente
# usará los fallbacks (`http://127.0.0.1:5002`) y la app no llegará al backend.
ARG NEXT_PUBLIC_DASHBOARD_API_URL
ARG NEXT_PUBLIC_DASHBOARD_HOTEL_ID=1
ARG NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL

ENV NEXT_PUBLIC_DASHBOARD_API_URL=${NEXT_PUBLIC_DASHBOARD_API_URL}
ENV NEXT_PUBLIC_DASHBOARD_HOTEL_ID=${NEXT_PUBLIC_DASHBOARD_HOTEL_ID}
ENV NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL=${NEXT_PUBLIC_ANALYSIS_WEBHOOK_URL}
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

############################
# Stage 3: runtime (standalone)
############################
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
