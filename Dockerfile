FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 app
COPY --chown=app:app backend ./backend
COPY --chown=app:app corpus ./corpus
COPY --chown=app:app docs/evaluation-results.json ./docs/evaluation-results.json
COPY --chown=app:app alembic.ini docker-entrypoint.sh ./
USER app
ENTRYPOINT ["/app/docker-entrypoint.sh"]
EXPOSE 8000
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]
