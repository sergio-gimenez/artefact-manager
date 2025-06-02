#!/bin/bash
set -x

# Artefact registry: Dockerhub
curl -X POST http://0.0.0.0:8000/artefact-exists \
  -H "Content-Type: application/json" \
  -d '{
    "registry_url": "docker.io/library/",
    "artefact_name": "nginx",
    "artefact_tag": "latest"
  }'

# Artefact registry: Harbor
# curl -X 'POST' \
#   'http://0.0.0.0:8000/artefact-exists' \
#   -H 'accept: application/json' \
#   -H 'Content-Type: application/json' \
#   -d '{
#   "src_registry_url": "registry.i2cat.net/sunrise6g-public/",
#   "src_artefact_name": "nginx",
#   "src_artefact_tag": "latest",
# }'
