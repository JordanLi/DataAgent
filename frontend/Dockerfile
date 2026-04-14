FROM dockerproxy.com/library/node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dockerproxy.com/library/node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV BACKEND_URL=http://backend:8000
RUN npm run build

FROM dockerproxy.com/library/node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S dataagent && adduser -S dataagent -G dataagent

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER dataagent
EXPOSE 3000
CMD ["node", "server.js"]
