FROM node:20-slim AS frontend-builder
WORKDIR /src
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build -- --outDir ../backend/app/static --emptyOutDir

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend-builder /src/backend/app/static ./app/static
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
