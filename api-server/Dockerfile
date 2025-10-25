FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

WORKDIR /app

COPY api-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY api-server/app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
