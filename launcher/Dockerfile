FROM python:3.10-slim

WORKDIR /

COPY . .

RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:5000", "launch:app"]
# CMD [ "python", "launch.py" ]