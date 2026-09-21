FROM python:3.14-slim

WORKDIR /src

COPY launcher/ /src/

RUN pip install .
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--timeout", "120", "--log-level", "info", "--bind", "0.0.0.0:5000", "launch:app"]
