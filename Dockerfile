FROM node:20-slim AS frontend-build
WORKDIR /build
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ frontend/
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /srv/app
COPY backend/ ./backend/
RUN pip install --no-cache-dir ./backend
COPY --from=frontend-build /build/frontend/dist ./frontend
ENV SPA_DIRECTORY=/srv/app/frontend
EXPOSE 8000
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
