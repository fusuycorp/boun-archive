# Stage 1: Build SvelteKit application
FROM oven/bun:1-alpine AS builder

WORKDIR /app

# Copy package configurations and lock files
COPY package.json bun.lock ./

# Install dependencies using Bun
RUN bun install --frozen-lockfile

# Copy remaining application source code
COPY . .

# Compile/build the application
RUN bun run build

# Stage 2: Serve using Alpine-Bun runner
FROM oven/bun:1-alpine AS runner

WORKDIR /app

# Switch to non-root user
USER bun

# Copy lockfile and package descriptor, install only production packages
COPY --chown=bun:bun package.json bun.lock ./
RUN bun install --frozen-lockfile --production

# Copy compiled build output from compiler stage
COPY --chown=bun:bun --from=builder /app/build ./build

# Set runtime options
ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000

# Serve SvelteKit application using Bun
CMD ["bun", "build/index.js"]
