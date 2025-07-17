import os
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from typing import Optional
from fastapi.responses import RedirectResponse

from src.skopeo.skopeo import SkopeoClient
from src.helm.helm import helm_registry_login, extract_registry_host, build_chart_reference

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


@app.post("/helm-chart", tags=["Artefact Management"])
async def upload_helm_chart(
    chart_file: UploadFile = File(
        ..., description="The packaged Helm chart (.tgz file)."
    ),
    registry_url: str = Form(..., description="Registry URL where the chart will be uploaded"),
    registry_username: Optional[str] = Form(None, description="Registry username (optional)"),
    registry_password: Optional[str] = Form(None, description="Registry password (optional)"),
) -> schemas.PostUploadHelmChartResponse:
    """
    API endpoint to upload a packaged Helm Chart to an OCI-compliant repository using Helm CLI.
    
    Parameters:
    - chart_file: The .tgz file containing the Helm chart
    - registry_url: Registry URL where the chart will be uploaded
    - registry_username: Registry username (optional)
    - registry_password: Registry password (optional)
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

            if registry_username and registry_password:
                registry_host = extract_registry_host(registry_url)
                helm_registry_login(
                    registry_host, registry_username, registry_password
                )

            helm_command = ["helm", "push", temp_chart.name, registry_url]
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


@app.delete("/helm-chart", tags=["Artefact Management"])
async def delete_helm_chart(
    chart: schemas.PostDeleteHelmChart,
) -> schemas.PostDeleteHelmChartResponse:
    """
    API endpoint to delete a Helm chart from an OCI-compliant repository.
    This uses Skopeo to delete the chart from the registry, which works with Harbor and other OCI registries.
    """
    try:
        if chart.registry_username and chart.registry_password:
            registry_host = extract_registry_host(chart.registry_url)
            helm_registry_login(
                registry_host, chart.registry_username, chart.registry_password
            )

        chart_ref = build_chart_reference(
            chart.registry_url, chart.chart_name, chart.chart_version
        )
        delete_cmd = ["skopeo", "delete", f"docker://{chart_ref}"]

        if chart.registry_username and chart.registry_password:
            delete_cmd.extend(
                ["--creds", f"{chart.registry_username}:{chart.registry_password}"]
            )

        result = subprocess.run(
            delete_cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error_message = result.stderr.strip()
            if (
                "unauthorized" in error_message.lower()
                or "invalid username/password" in error_message.lower()
            ):
                raise RuntimeError(f"Authentication failed: {error_message}")
            elif "not found" in error_message.lower():
                raise RuntimeError(
                    f"Helm chart {chart.chart_name}:{chart.chart_version} not found in registry"
                )
            else:
                raise RuntimeError(f"Helm chart deletion failed: {error_message}")

        return schemas.PostDeleteHelmChartResponse(
            success=True,
            detail=f"Helm chart {chart.chart_name}:{chart.chart_version} deleted successfully.",
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
