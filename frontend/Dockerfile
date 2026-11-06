# ==============================================================================
# WindForecast Analytics - React Frontend Dockerfile (Multi-Stage Build)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies reproducibly
COPY package.json package-lock.json ./
RUN npm ci

# Accept build-time API base URL (empty defaults to Nginx reverse-proxy in production)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy frontend source files
COPY index.html vite.config.js ./
COPY public/ ./public/
COPY src/ ./src/

# Build static production bundle into /app/dist
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Server (Lightweight Nginx Alpine)
# ------------------------------------------------------------------------------
FROM nginx:alpine AS runner

# Remove default Nginx welcome assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration (SPA fallback + /api/ reverse proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Run Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

