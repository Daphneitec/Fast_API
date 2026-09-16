FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY abacus ./abacus

ENV ABACUS_STORE=redis
ENV ABACUS_REDIS_URL=redis://redis:6379/0
EXPOSE 8000
CMD ["uvicorn", "abacus.main:app", "--host", "0.0.0.0", "--port", "8000"]
