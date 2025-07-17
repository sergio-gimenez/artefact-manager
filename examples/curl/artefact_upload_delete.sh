#!/bin/bash

# Example script showing how to upload and delete an artefact using the new generalized /artefact endpoints
# This example uses a HELM artefact type, but the API now supports specifying the artefact type
#
# Usage: Make sure you have a hello-0.1.2.tgz file in the current directory, then run:
# ./artefact_upload_delete.sh

echo "Uploading artefact..."
curl -X 'POST' \
  'http://127.0.0.1:8000/artefact' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'artefact_file=@hello-0.1.2.tgz;type=application/x-compressed-tar' \
  -F 'artefact_type=HELM' \
  -F 'registry_url=oci://demo.goharbor.io/test_sunrise' \
  -F 'registry_username=mail@example.org' \
  -F 'registry_password=secretpassword'

echo -e "\n\nDeleting artefact..."
curl -X 'DELETE' \
  'http://127.0.0.1:8000/artefact' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "registry_url": "oci://demo.goharbor.io/test_sunrise",
  "artefact_name": "hello",
  "artefact_version": "0.1.2",
  "registry_username": "mail@example.org",
  "registry_password": "secretpassword"
}'

echo -e "\n\nDone!"
