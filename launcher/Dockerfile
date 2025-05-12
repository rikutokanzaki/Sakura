FROM python:3.8

WORKDIR /

COPY . .

RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1

CMD ["python", "launch.py"]