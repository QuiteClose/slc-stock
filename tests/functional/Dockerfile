FROM python:3.11-slim
WORKDIR /app
ENV XDG_CACHE_HOME=/var/cache
RUN mkdir -p /var/cache && chmod -R 0777 /var/cache
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt
COPY tests/functional/requirements.txt /app/tests/functional/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /app/tests/functional/requirements.txt
RUN playwright install --with-deps chromium
CMD ["pytest", "tests/functional/"]
