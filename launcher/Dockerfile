FROM python:3.10-slim

WORKDIR /src

COPY . .

RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--chdir", "src", "--timeout", "120", "--log-level", "info", "--bind", "0.0.0.0:5000", "launch:app"]
