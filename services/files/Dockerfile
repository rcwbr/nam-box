FROM python:3.12.4-slim

WORKDIR /app

RUN --mount=type=bind,source=requirements.txt,destination=/tmp/requirements.txt \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY file_api.py file_api.py

CMD ["uvicorn", "file_api:get_app", "--host", "0.0.0.0", "--port", "80"]
