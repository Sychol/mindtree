FROM node:20-bookworm-slim

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

COPY . .

RUN if [ -f package-lock.json ]; then \
      npm ci; \
    elif [ -f package.json ]; then \
      npm install; \
    else \
      echo "TODO phase05: add package.json with React/Vite dependencies."; \
    fi

EXPOSE 5173

# TODO(phase05): replace the fallback branch after the Vite app exists.
CMD ["sh", "-c", "if [ -f package.json ]; then npm run dev -- --host 0.0.0.0 --port 5173; else echo 'TODO phase05: React/Vite app is not implemented yet.'; sleep infinity; fi"]
