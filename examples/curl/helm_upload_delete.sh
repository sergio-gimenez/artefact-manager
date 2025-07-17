curl -X 'POST' \
  'http://127.0.0.1:8000/helm-chart' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'chart_file=@hello-0.1.2.tgz;type=application/x-compressed-tar' \
  -F 'registry_url=oci://demo.goharbor.io/test_sunrise' \
  -F 'registry_username=mail@example.org' \
  -F 'registry_password=secretpassword'

curl -X 'DELETE' \
  'http://127.0.0.1:8000/helm-chart' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "registry_url": "oci://demo.goharbor.io/test_sunrise",
  "chart_name": "hello",
  "chart_version": "0.1.2",
  "registry_username": "mail@example.org",
  "registry_password": "secretpassword"
}'