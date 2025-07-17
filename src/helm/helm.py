"""
Helm helper functions for registry operations.
"""
import subprocess


def helm_registry_login(registry_host: str, username: str, password: str) -> None:
    """
    Perform Helm registry login.

    Args:
        registry_host: The registry hostname
        username: Registry username
        password: Registry password

    Raises:
        RuntimeError: If login fails
    """
    login_cmd = [
        "helm",
        "registry",
        "login",
        registry_host,
        "-u",
        username,
        "-p",
        password,
    ]
    login_result = subprocess.run(login_cmd, capture_output=True, text=True)
    if login_result.returncode != 0:
        raise RuntimeError(f"Helm registry login failed: {login_result.stderr.strip()}")


def extract_registry_host(registry_url: str) -> str:
    """
    Extract registry host from OCI URL.

    Args:
        registry_url: The full OCI registry URL

    Returns:
        The registry hostname
    """
    return registry_url.replace("oci://", "").split("/")[0]


def build_chart_reference(
    registry_url: str, chart_name: str, chart_version: str
) -> str:
    """
    Build a proper chart reference for deletion.

    Args:
        registry_url: The OCI registry URL
        chart_name: The chart name
        chart_version: The chart version

    Returns:
        The complete chart reference
    """
    registry_base = registry_url.replace("oci://", "").rstrip("/")
    if "/" in chart_name:
        # chart_name already includes the project path, use it directly
        chart_ref = f"{registry_base.split('/')[0]}/{chart_name}:{chart_version}"
    else:
        # chart_name doesn't include project, so add the full registry path
        chart_ref = f"{registry_base}/{chart_name}:{chart_version}"
    return chart_ref
