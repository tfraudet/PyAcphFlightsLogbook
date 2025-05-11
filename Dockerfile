FROM python:3.9.22-slim-bookworm
# FROM python:3.9.22-slim-bullseye
# FROM python:3.8.20-slim-bookworm
# FROM python:3.8.20-alpine

ARG KEEP_CONTAINER_ALIVE
ENV KEEP_CONTAINER_ALIVE=${KEEP_CONTAINER_ALIVE:-1}

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
	build-essential \
	curl \
	software-properties-common \
	git \
	&& rm -rf /var/lib/apt/lists/*

COPY . .

# make a data directory for the logs
RUN mkdir -p /app/logs

# install python dependencies
RUN pip3 install -r requirements.txt

RUN chmod +x entrypoint.sh

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Set the command to run when the container starts
# ENTRYPOINT ["python", "acph-logbook.py", "-i", "./acph-logbook-local.ini"]
ENTRYPOINT ["./entrypoint.sh"]

