FROM mcr.microsoft.com/playwright/python:latest

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Force install matching browser versions
RUN playwright install --with-deps chromium

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
