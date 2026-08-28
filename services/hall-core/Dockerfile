FROM python:3.12-slim
ARG HALL_BUILD_COMMIT=unknown
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HALL_BUILD_COMMIT=${HALL_BUILD_COMMIT}
RUN groupadd -g 10001 hall && useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin hall \
    && install -d -o hall -g hall -m 0700 /var/lib/hall-core
WORKDIR /app
COPY services/hall-core/app.py /app/app.py
RUN python -m py_compile /app/app.py
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz',timeout=3).read()"
CMD ["python", "/app/app.py"]
