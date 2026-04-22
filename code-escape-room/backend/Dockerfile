FROM python:3.11

WORKDIR /app

# 🔧 תיקון SSL קריטי
RUN apt-get update && apt-get install -y ca-certificates && update-ca-certificates

# upgrade pip
RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]