FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libblas-dev \
    liblapack-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY best.pt .

COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install  --no-cache-dir -r requirements.txt
RUN pip uninstall jwt

COPY ../../Downloads/my_app_fastapi-main .

EXPOSE 9000

ENV HOST 0.0.0.0

CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:9000", "app.main:app"]
