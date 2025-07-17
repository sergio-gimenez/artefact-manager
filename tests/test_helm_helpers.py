"""
Unit tests for Helm chart helper functions.
"""

from unittest.mock import Mock, patch
import pytest

from src.helm.helm import (
    helm_registry_login,
    extract_registry_host,
    build_chart_reference,
)


class TestHelmChartHelpers:
    """Test helper functions for Helm chart operations."""

    @patch("src.helm.helm.subprocess.run")
    def test_helm_registry_login_success(self, mock_run):
        """Test successful Helm registry login."""
        mock_run.return_value = Mock(returncode=0)

        # Should not raise an exception
        helm_registry_login("registry.example.com", "user", "pass")

        mock_run.assert_called_once_with(
            ["helm", "registry", "login", "registry.example.com", "-u", "user", "-p", "pass"],
            capture_output=True,
            text=True,
        )

    @patch("src.helm.helm.subprocess.run")
    def test_helm_registry_login_failure(self, mock_run):
        """Test failed Helm registry login."""
        mock_run.return_value = Mock(returncode=1, stderr="login failed")

        with pytest.raises(RuntimeError, match="Helm registry login failed: login failed"):
            helm_registry_login("registry.example.com", "user", "pass")

    def test_extract_registry_host(self):
        """Test registry host extraction from OCI URL."""
        assert (
            extract_registry_host("oci://registry.example.com/project")
            == "registry.example.com"
        )
        assert (
            extract_registry_host("oci://harbor.company.com:5000/library")
            == "harbor.company.com:5000"
        )

    def test_build_chart_reference_with_project_in_name(self):
        """Test chart reference building when chart name includes project path."""
        result = build_chart_reference(
            "oci://registry.example.com/project", "subproject/chart-name", "1.0.0"
        )
        assert result == "registry.example.com/subproject/chart-name:1.0.0"

    def test_build_chart_reference_without_project_in_name(self):
        """Test chart reference building when chart name doesn't include project path."""
        result = build_chart_reference(
            "oci://registry.example.com/project", "chart-name", "1.0.0"
        )
        assert result == "registry.example.com/project/chart-name:1.0.0"
