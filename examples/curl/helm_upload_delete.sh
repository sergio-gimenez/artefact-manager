#!/bin/bash

# DEPRECATED: This script has been renamed to artefact_upload_delete.sh
# This is kept for backward compatibility but will be removed in a future version.

echo "WARNING: helm_upload_delete.sh is deprecated. Please use artefact_upload_delete.sh instead."
echo "Running artefact_upload_delete.sh..."
echo

# Execute the new script
exec "$(dirname "$0")/artefact_upload_delete.sh"
