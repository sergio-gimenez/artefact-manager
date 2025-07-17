"""
Unit tests for Helm chart upload endpoint.
"""

from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.api import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestHelmChartUpload:
    """Test Helm chart upload endpoint."""

    def test_upload_helm_chart_invalid_file_extension(self, client):
        """Test upload with invalid file extension."""
        files = {"chart_file": ("chart.zip", b"fake content", "application/zip")}
        data = {
            "registry_url": "oci://registry.example.com/project"
        }

        response = client.post("/helm-chart", files=files, data=data)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_helm_chart_missing_registry_url(self, client):
        """Test upload with missing registry_url parameter."""
        files = {"chart_file": ("chart.tgz", b"fake content", "application/gzip")}
        data = {}  # Missing registry_url

        response = client.post("/helm-chart", files=files, data=data)

        assert response.status_code == 422  # Validation error
        assert "registry_url" in str(response.json())

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_upload_helm_chart_success_with_auth(self, mock_login, mock_run, client):
        """Test successful Helm chart upload with authentication."""
        mock_run.return_value = Mock(returncode=0)  # Mock successful helm push
        # Create fake .tgz file
        chart_content = b"fake helm chart content"
        files = {"chart_file": ("chart.tgz", chart_content, "application/gzip")}
        data = {
            "registry_url": "oci://registry.example.com/project",
            "registry_username": "user",
            "registry_password": "pass",
        }
        response = client.post("/helm-chart", files=files, data=data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "uploaded successfully" in response_data["detail"]
        mock_login.assert_called_once_with("registry.example.com", "user", "pass")

    @patch("src.api.api.subprocess.run")
    def test_upload_helm_chart_success_without_auth(self, mock_run, client):
        """Test successful Helm chart upload without authentication."""
        mock_run.return_value = Mock(returncode=0)  # Mock successful helm push
        chart_content = b"fake helm chart content"
        files = {"chart_file": ("chart.tgz", chart_content, "application/gzip")}
        data = {
            "registry_url": "oci://registry.example.com/project"
        }
        response = client.post("/helm-chart", files=files, data=data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_upload_helm_chart_push_failure(self, mock_login, mock_run, client):
        """Test Helm chart upload when push fails."""
        mock_run.return_value = Mock(returncode=1, stderr="push failed")  # Mock failed helm push
        chart_content = b"fake helm chart content"
        files = {"chart_file": ("chart.tgz", chart_content, "application/gzip")}
        data = {
            "registry_url": "oci://registry.example.com/project",
            "registry_username": "user",
            "registry_password": "pass",
        }
        response = client.post("/helm-chart", files=files, data=data)
        assert response.status_code == 500
        assert "Helm push failed" in response.json()["detail"]

    @patch("src.api.api.helm_registry_login")
    def test_upload_helm_chart_login_failure(self, mock_login, client):
        """Test Helm chart upload when login fails."""
        mock_login.side_effect = RuntimeError("login failed")  # Mock failed login
        chart_content = b"fake helm chart content"
        files = {"chart_file": ("chart.tgz", chart_content, "application/gzip")}
        data = {
            "registry_url": "oci://registry.example.com/project",
            "registry_username": "user",
            "registry_password": "pass",
        }
        response = client.post("/helm-chart", files=files, data=data)
        assert response.status_code == 500
        assert "login failed" in response.json()["detail"]
