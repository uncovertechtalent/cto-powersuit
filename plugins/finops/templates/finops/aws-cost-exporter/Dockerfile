FROM python:3.12-slim
RUN pip install --no-cache-dir boto3==1.35.0
WORKDIR /app
COPY exporter.py .
# Runs as the host user that owns ~/.aws (mode 600), so the read-only mount is readable.
# /data holds the response cache; a new named volume takes this ownership.
ARG UID=1000
ARG GID=1000
RUN mkdir /data && chown ${UID}:${GID} /data
USER ${UID}:${GID}
EXPOSE 9202
CMD ["python", "exporter.py"]
