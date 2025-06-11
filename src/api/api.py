import os
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse

from src.skopeo.skopeo import SkopeoClient

from . import schemas

app = FastAPI(
    title="Artefact Manager API",
    description="WIP API for managing artefacts using Skopeo.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Artefact Management",
            "description": ("Operations related to artefact management " "registries."),
        }
    ],
)


@app.get("/", include_in_schema=False)
def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.post("/artefact-exists", tags=["Artefact Management"])
def artefact_exists(
    artefact: schemas.PostArtefactExists,
) -> schemas.PostArtefactExistsResponse:
    """
    API endpoint to check if a Helm Chart or container image with a specific
    tag exists in a repository.
    """
    try:
        exists = SkopeoClient.artefact_exists(
            registry_url=artefact.registry_url,
            artefact_name=artefact.artefact_name,
            artefact_tag=artefact.artefact_tag,
            registry_username=artefact.registry_username,
            registry_password=artefact.registry_password,
        )
        return schemas.PostArtefactExistsResponse(exists=exists)

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Uncategorized error: " + str(e))


@app.post("/copy-artefact", tags=["Artefact Management"])
def copy_artefact(
    artefact: schemas.PostCopyArtefact,
) -> schemas.PostCopyArtefactResponse:
    """
    API Endpoint to copy a Helm Chart/container image from one registry
    to another.
    """
    try:
        dst_name = artefact.dst_artefact_name or artefact.src_artefact_name
        dst_tag = artefact.dst_artefact_tag or artefact.src_artefact_tag

        success = SkopeoClient.copy_artefact(
            src_registry_url=artefact.src_registry_url,
            src_artefact_name=artefact.src_artefact_name,
            src_artefact_tag=artefact.src_artefact_tag,
            dst_registry_url=artefact.dst_registry_url,
            dst_artefact_name=dst_name,
            dst_artefact_tag=dst_tag,
            src_registry_username=artefact.src_registry_username,
            src_registry_password=artefact.src_registry_password,
            dst_registry_username=artefact.dst_registry_username,
            dst_registry_password=artefact.dst_registry_password,
        )
        return schemas.PostCopyArtefactResponse(success=success)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-helm-chart", tags=["Artefact Management"])
async def upload_helm_chart(
    chart_file: UploadFile = File(
        ..., description="The packaged Helm chart (.tgz file)."
    ),
    registry_url: str = Form(..., description="URL of the OCI registry."),
    registry_username: str | None = Form(
        None, description="Username for the OCI registry."
    ),
    registry_password: str | None = Form(
        None, description="Password for the OCI registry."
    ),
) -> schemas.PostUploadHelmChartResponse:
    """
    API endpoint to upload a packaged Helm Chart to an OCI-compliant repository using Helm CLI.
    """
    if not chart_file.filename or not chart_file.filename.endswith(".tgz"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a packaged Helm chart (.tgz).",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".tgz") as temp_chart:
            content = await chart_file.read()
            temp_chart.write(content)
            temp_chart.flush()

            # 1. Login to the registry if credentials are provided
            if registry_username and registry_password:
                login_cmd = [
                    "helm", "registry", "login",
                    registry_url.replace("oci://", "").split("/")[0],
                    "-u", registry_username,
                    "-p", registry_password
                ]
                login_result = subprocess.run(
                    login_cmd, capture_output=True, text=True
                )
                if login_result.returncode != 0:
                    raise RuntimeError(f"Helm registry login failed: {login_result.stderr.strip()}")

            # 2. Push the chart
            helm_command = [
                "helm", "push", temp_chart.name, registry_url
            ]
            result = subprocess.run(
                helm_command,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Helm push failed: {result.stderr.strip()}")

        return schemas.PostUploadHelmChartResponse(
            success=True, detail="Helm chart uploaded successfully."
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
    finally:
        await chart_file.close()


# @app.post("/placeholder")
# def placeholder(
#     artefact: schemas.PostPlaceholder
# ) -> schemas.PostPlaceholderResponse:
#     raise HTTPException(status_code=501, detail="Not implemented")
