import subprocess
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from src.helm.helm import (
    build_chart_reference,
    extract_registry_host,
    helm_registry_login,
)
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


@app.post("/artefact", tags=["Artefact Management"])
async def upload_artefact(
    artefact_file: UploadFile = File(
        ..., description="The packaged artefact (.tgz file)."
    ),
    artefact_type: schemas.ArtefactType = Form(
        ..., description="Type of artefact being uploaded"
    ),
    registry_url: str = Form(
        ..., description="Registry URL where the artefact will be uploaded"
    ),
    registry_username: Optional[str] = Form(
        None, description="Registry username (optional)"
    ),
    registry_password: Optional[str] = Form(
        None, description="Registry password (optional)"
    ),
) -> schemas.PostUploadArtefactResponse:
    """
    API endpoint to upload a packaged artefact to an OCI-compliant repository.
    Currently supports HELM charts using Helm CLI.

    Parameters:
    - artefact_file: The .tgz file containing the artefact
    - artefact_type: Type of artefact (currently only HELM is supported)
    - registry_url: Registry URL where the artefact will be uploaded
    - registry_username: Registry username (optional)
    - registry_password: Registry password (optional)
    """
    if not artefact_file.filename or not artefact_file.filename.endswith(".tgz"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a packaged artefact (.tgz).",
        )

    # XXX Currently only HELM type is supported
    if artefact_type != schemas.ArtefactType.HELM:
        raise HTTPException(
            status_code=400,
            detail=f"Artefact type {artefact_type} is not currently supported. Only HELM is supported.",
        )

    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".tgz") as temp_chart:
            content = await artefact_file.read()
            temp_chart.write(content)
            temp_chart.flush()

            if registry_username and registry_password:
                registry_host = extract_registry_host(registry_url)
                helm_registry_login(registry_host, registry_username, registry_password)

            helm_command = ["helm", "push", temp_chart.name, registry_url]
            result = subprocess.run(
                helm_command,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Helm push failed: {result.stderr.strip()}")

        return schemas.PostUploadArtefactResponse(
            success=True, detail="Artefact uploaded successfully."
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
    finally:
        await artefact_file.close()


@app.delete("/artefact", tags=["Artefact Management"])
async def delete_artefact(
    artefact: schemas.PostDeleteArtefact,
) -> schemas.PostDeleteArtefactResponse:
    """
    <<<<<<< Updated upstream
        API endpoint to delete a Helm chart from an OCI-compliant repository.
        This uses Skopeo to delete the chart from the registry, which works with Harbor and other OCI registries.
    =======
        API endpoint to delete an artefact from an OCI-compliant repository.
        This uses Skopeo to delete the artefact from the registry, beware that skopeo will
        mark the artefact for later deletion by the registry's garbage collector
    >>>>>>> Stashed changes
    """
    try:
        if artefact.registry_username and artefact.registry_password:
            registry_host = extract_registry_host(artefact.registry_url)
            helm_registry_login(
                registry_host, artefact.registry_username, artefact.registry_password
            )

        artefact_ref = build_chart_reference(
            artefact.registry_url, artefact.artefact_name, artefact.artefact_version
        )
        delete_cmd = ["skopeo", "delete", f"docker://{artefact_ref}"]

        if artefact.registry_username and artefact.registry_password:
            delete_cmd.extend(
                [
                    "--creds",
                    f"{artefact.registry_username}:{artefact.registry_password}",
                ]
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
                    f"Artefact {artefact.artefact_name}:{artefact.artefact_version} not found in registry"
                )
            else:
                raise RuntimeError(f"Artefact deletion failed: {error_message}")

        return schemas.PostDeleteArtefactResponse(
            success=True,
            detail=f"Artefact {artefact.artefact_name}:{artefact.artefact_version} deleted successfully.",
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
