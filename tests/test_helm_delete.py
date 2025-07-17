"""
Unit tests for Helm chart delete endpoint.
"""

from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from src.api.api import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestHelmChartDelete:
    """Test Helm chart delete endpoint."""

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_delete_helm_chart_success_with_auth(self, mock_login, mock_run, client):
        """Test successful Helm chart deletion with authentication."""
        # Mock successful skopeo delete
        mock_run.return_value = Mock(returncode=0)

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "my-chart",
            "chart_version": "1.0.0",
            "registry_username": "user",
            "registry_password": "pass",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert "deleted successfully" in response_data["detail"]

        # Verify login was called
        mock_login.assert_called_once_with("registry.example.com", "user", "pass")

    @patch("src.api.api.subprocess.run")
    def test_delete_helm_chart_success_without_auth(self, mock_run, client):
        """Test successful Helm chart deletion without authentication."""
        # Mock successful skopeo delete
        mock_run.return_value = Mock(returncode=0)

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "my-chart",
            "chart_version": "1.0.0",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_delete_helm_chart_not_found(self, mock_login, mock_run, client):
        """Test Helm chart deletion when chart is not found."""
        # Mock skopeo delete with not found error
        mock_run.return_value = Mock(returncode=1, stderr="manifest unknown: not found")

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "my-chart",
            "chart_version": "1.0.0",
            "registry_username": "user",
            "registry_password": "pass",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 500
        assert "not found in registry" in response.json()["detail"]

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_delete_helm_chart_auth_failed(self, mock_login, mock_run, client):
        """Test Helm chart deletion when authentication fails."""
        # Mock skopeo delete with auth error
        mock_run.return_value = Mock(
            returncode=1, stderr="unauthorized: authentication required"
        )

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "my-chart",
            "chart_version": "1.0.0",
            "registry_username": "user",
            "registry_password": "wrongpass",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 500
        assert "Authentication failed" in response.json()["detail"]

    @patch("src.api.api.helm_registry_login")
    def test_delete_helm_chart_login_failure(self, mock_login, client):
        """Test Helm chart deletion when login fails."""
        # Mock failed login
        mock_login.side_effect = RuntimeError("login failed")

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "my-chart",
            "chart_version": "1.0.0",
            "registry_username": "user",
            "registry_password": "pass",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 500
        assert "login failed" in response.json()["detail"]

    @patch("src.api.api.subprocess.run")
    @patch("src.api.api.helm_registry_login")
    def test_delete_helm_chart_builds_correct_reference(
        self, mock_login, mock_run, client
    ):
        """Test that delete builds the correct chart reference."""
        # Mock successful skopeo delete
        mock_run.return_value = Mock(returncode=0)

        payload = {
            "registry_url": "oci://registry.example.com/project",
            "chart_name": "subproject/my-chart",
            "chart_version": "1.0.0",
            "registry_username": "user",
            "registry_password": "pass",
        }

        response = client.request("DELETE", "/helm-chart", json=payload)

        assert response.status_code == 200

        # Verify the correct skopeo command was called
        expected_cmd = [
            "skopeo",
            "delete",
            "docker://registry.example.com/subproject/my-chart:1.0.0",
            "--creds",
            "user:pass",
        ]
        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True)
