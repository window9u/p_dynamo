FROM python:3.12-bookworm as builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim-bookworm as runner

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY ./app /app/app

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
