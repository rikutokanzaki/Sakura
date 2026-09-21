FROM python:3.14-slim

WORKDIR /tests

RUN pip install --no-cache-dir paramiko pytest requests

COPY tests/e2e/ /tests/

CMD ["pytest", "-q", "test_sakura_e2e.py", "-s"]
