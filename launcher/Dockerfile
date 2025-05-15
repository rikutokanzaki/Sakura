FROM python:3.10-slim

WORKDIR /

COPY . .

RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1

# CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:5000", "launch:app"]
CMD [ "python", "launch.py" ]