"""Tests for docker_service — business logic with mocked Docker SDK."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jarvis_mcp.services import docker_service


def make_mock_container(
    name: str,
    status: str = "running",
    image_tags: list[str] | None = None,
    labels: dict[str, str] | None = None,
    ports: dict | None = None,
    logs_output: bytes = b"",
) -> MagicMock:
    """Build a mock Container object matching the Docker SDK interface."""
    container = MagicMock()
    container.name = name
    container.status = status
    container.labels = labels or {}
    container.ports = ports or {}
    container.logs.return_value = logs_output

    image = MagicMock()
    image.tags = image_tags or [f"{name}:latest"]
    image.id = "sha256:abc123"
    container.image = image

    return container


# ---------------------------------------------------------------------------
# _is_jarvis_container
# ---------------------------------------------------------------------------


class TestIsJarvisContainer:
    def test_name_contains_jarvis(self):
        c = make_mock_container("jarvis-auth")
        assert docker_service._is_jarvis_container(c) is True

    def test_label_contains_jarvis(self):
        c = make_mock_container(
            "some-random-name",
            labels={"com.docker.compose.project": "jarvis-auth"},
        )
        assert docker_service._is_jarvis_container(c) is True

    def test_known_infra_name(self):
        for infra in ("loki", "grafana", "mosquitto", "minio", "postgres", "redis"):
            c = make_mock_container(f"jarvis-{infra}")
            assert docker_service._is_jarvis_container(c) is True

    def test_bare_infra_name(self):
        c = make_mock_container("loki")
        assert docker_service._is_jarvis_container(c) is True

    def test_non_jarvis_container(self):
        c = make_mock_container("nginx-proxy")
        assert docker_service._is_jarvis_container(c) is False

    def test_empty_name(self):
        c = make_mock_container("")
        c.name = ""
        assert docker_service._is_jarvis_container(c) is False


# ---------------------------------------------------------------------------
# _find_jarvis_container
# ---------------------------------------------------------------------------


class TestFindJarvisContainer:
    def _setup_client(self, containers: list[MagicMock]) -> MagicMock:
        client = MagicMock()
        client.containers.list.return_value = containers
        return client

    def test_exact_match(self):
        auth = make_mock_container("jarvis-auth")
        tts = make_mock_container("jarvis-tts")
        client = self._setup_client([auth, tts])

        with patch.object(docker_service, "_get_client", return_value=client):
            result = docker_service._find_jarvis_container("jarvis-auth")
        assert result is auth

    def test_partial_match(self):
        auth = make_mock_container("jarvis-auth")
        client = self._setup_client([auth])

        with patch.object(docker_service, "_get_client", return_value=client):
            result = docker_service._find_jarvis_container("auth")
        assert result is auth

    def test_no_match_raises(self):
        auth = make_mock_container("jarvis-auth")
        client = self._setup_client([auth])

        with patch.object(docker_service, "_get_client", return_value=client):
            with pytest.raises(ValueError, match="No jarvis container"):
                docker_service._find_jarvis_container("nonexistent")

    def test_ambiguous_match_raises(self):
        auth = make_mock_container("jarvis-auth")
        auth2 = make_mock_container("jarvis-auth-worker")
        client = self._setup_client([auth, auth2])

        with patch.object(docker_service, "_get_client", return_value=client):
            with pytest.raises(ValueError, match="Ambiguous"):
                docker_service._find_jarvis_container("auth")

    def test_exact_match_beats_partial(self):
        """Exact match should win even when partials exist."""
        auth = make_mock_container("jarvis-auth")
        auth_worker = make_mock_container("jarvis-auth-worker")
        client = self._setup_client([auth, auth_worker])

        with patch.object(docker_service, "_get_client", return_value=client):
            result = docker_service._find_jarvis_container("jarvis-auth")
        assert result is auth

    def test_non_jarvis_containers_ignored(self):
        nginx = make_mock_container("nginx-proxy")
        auth = make_mock_container("jarvis-auth")
        client = self._setup_client([nginx, auth])

        with patch.object(docker_service, "_get_client", return_value=client):
            with pytest.raises(ValueError, match="No jarvis container"):
                docker_service._find_jarvis_container("nginx")


# ---------------------------------------------------------------------------
# list_containers
# ---------------------------------------------------------------------------


class TestListContainers:
    def test_returns_jarvis_only(self):
        auth = make_mock_container("jarvis-auth", ports={"7701/tcp": [{"HostPort": "7701"}]})
        nginx = make_mock_container("nginx-proxy")
        client = MagicMock()
        client.containers.list.return_value = [auth, nginx]

        with patch.object(docker_service, "_get_client", return_value=client):
            result = docker_service.list_containers()

        assert len(result) == 1
        assert result[0]["name"] == "jarvis-auth"
        assert "7701" in result[0]["ports"]

    def test_show_all_passed_to_sdk(self):
        client = MagicMock()
        client.containers.list.return_value = []

        with patch.object(docker_service, "_get_client", return_value=client):
            docker_service.list_containers(show_all=True)
            client.containers.list.assert_called_once_with(all=True)

    def test_empty_ports(self):
        c = make_mock_container("jarvis-tts", ports={})
        client = MagicMock()
        client.containers.list.return_value = [c]

        with patch.object(docker_service, "_get_client", return_value=client):
            result = docker_service.list_containers()

        assert result[0]["ports"] == ""


# ---------------------------------------------------------------------------
# get_container_logs
# ---------------------------------------------------------------------------


class TestGetContainerLogs:
    def test_returns_decoded_logs(self):
        c = make_mock_container("jarvis-auth", logs_output=b"2024-01-01 INFO started\n")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            logs = docker_service.get_container_logs("auth", lines=50)

        assert "INFO started" in logs
        c.logs.assert_called_once_with(tail=50, timestamps=True)

    def test_lines_capped_at_1000(self):
        c = make_mock_container("jarvis-auth", logs_output=b"line\n")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            docker_service.get_container_logs("auth", lines=5000)

        c.logs.assert_called_once_with(tail=1000, timestamps=True)

    def test_since_parameter(self):
        c = make_mock_container("jarvis-auth", logs_output=b"")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            docker_service.get_container_logs("auth", since="1h")

        c.logs.assert_called_once_with(tail=100, timestamps=True, since="1h")


# ---------------------------------------------------------------------------
# restart / stop / start
# ---------------------------------------------------------------------------


class TestContainerLifecycle:
    def test_restart(self):
        c = make_mock_container("jarvis-auth")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            msg = docker_service.restart_container("auth")

        c.restart.assert_called_once_with(timeout=30)
        assert "restarted" in msg

    def test_stop_running(self):
        c = make_mock_container("jarvis-auth", status="running")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            msg = docker_service.stop_container("auth")

        c.stop.assert_called_once_with(timeout=30)
        assert "stopped" in msg

    def test_stop_already_stopped(self):
        c = make_mock_container("jarvis-auth", status="exited")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            msg = docker_service.stop_container("auth")

        c.stop.assert_not_called()
        assert "already" in msg

    def test_start_stopped(self):
        c = make_mock_container("jarvis-auth", status="exited")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            msg = docker_service.start_container("auth")

        c.start.assert_called_once()
        assert "started" in msg

    def test_start_already_running(self):
        c = make_mock_container("jarvis-auth", status="running")

        with patch.object(docker_service, "_find_jarvis_container", return_value=c):
            msg = docker_service.start_container("auth")

        c.start.assert_not_called()
        assert "already running" in msg


# ---------------------------------------------------------------------------
# _discover_service_dirs
# ---------------------------------------------------------------------------


class TestDiscoverServiceDirs:
    def test_finds_services_with_compose(self, tmp_path: Path):
        # Create service directories with compose files
        auth_dir = tmp_path / "jarvis-auth"
        auth_dir.mkdir()
        (auth_dir / "docker-compose.yaml").touch()

        tts_dir = tmp_path / "jarvis-tts"
        tts_dir.mkdir()
        (tts_dir / "compose.yml").touch()

        # Non-jarvis dir should be ignored
        other_dir = tmp_path / "other-service"
        other_dir.mkdir()
        (other_dir / "docker-compose.yaml").touch()

        # Jarvis dir without compose file should be ignored
        no_compose = tmp_path / "jarvis-node-setup"
        no_compose.mkdir()

        with patch.object(docker_service.config, "jarvis_root", str(tmp_path)):
            services = docker_service._discover_service_dirs()

        assert "jarvis-auth" in services
        assert "jarvis-tts" in services
        assert "other-service" not in services
        assert "jarvis-node-setup" not in services

    def test_nonexistent_root(self, tmp_path: Path):
        with patch.object(docker_service.config, "jarvis_root", str(tmp_path / "nonexistent")):
            services = docker_service._discover_service_dirs()

        assert services == {}


# ---------------------------------------------------------------------------
# compose_up / compose_down
# ---------------------------------------------------------------------------


class TestComposeCommands:
    def test_compose_up(self, tmp_path: Path):
        svc_dir = tmp_path / "jarvis-auth"
        svc_dir.mkdir()
        (svc_dir / "docker-compose.yaml").touch()

        with (
            patch.object(docker_service.config, "jarvis_root", str(tmp_path)),
            patch.object(docker_service, "subprocess") as mock_subprocess,
        ):
            mock_result = MagicMock()
            mock_result.stdout = "Creating jarvis-auth ... done"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_subprocess.run.return_value = mock_result

            output = docker_service.compose_up("jarvis-auth")

        mock_subprocess.run.assert_called_once()
        call_args = mock_subprocess.run.call_args
        assert call_args[0][0] == ["docker", "compose", "up", "-d"]
        assert call_args[1]["cwd"] == str(svc_dir)
        assert "done" in output

    def test_compose_down(self, tmp_path: Path):
        svc_dir = tmp_path / "jarvis-auth"
        svc_dir.mkdir()
        (svc_dir / "docker-compose.yaml").touch()

        with (
            patch.object(docker_service.config, "jarvis_root", str(tmp_path)),
            patch.object(docker_service, "subprocess") as mock_subprocess,
        ):
            mock_result = MagicMock()
            mock_result.stdout = "Stopping jarvis-auth ... done"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_subprocess.run.return_value = mock_result

            output = docker_service.compose_down("jarvis-auth")

        mock_subprocess.run.assert_called_once()
        call_args = mock_subprocess.run.call_args
        assert call_args[0][0] == ["docker", "compose", "down"]

    def test_compose_accepts_short_name(self, tmp_path: Path):
        svc_dir = tmp_path / "jarvis-auth"
        svc_dir.mkdir()
        (svc_dir / "docker-compose.yaml").touch()

        with (
            patch.object(docker_service.config, "jarvis_root", str(tmp_path)),
            patch.object(docker_service, "subprocess") as mock_subprocess,
        ):
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_subprocess.run.return_value = mock_result

            docker_service.compose_up("auth")

        mock_subprocess.run.assert_called_once()

    def test_compose_unknown_service_raises(self, tmp_path: Path):
        with patch.object(docker_service.config, "jarvis_root", str(tmp_path)):
            with pytest.raises(ValueError, match="No compose file"):
                docker_service.compose_up("nonexistent")

    def test_compose_failure(self, tmp_path: Path):
        svc_dir = tmp_path / "jarvis-auth"
        svc_dir.mkdir()
        (svc_dir / "docker-compose.yaml").touch()

        with (
            patch.object(docker_service.config, "jarvis_root", str(tmp_path)),
            patch.object(docker_service, "subprocess") as mock_subprocess,
        ):
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = "error: no such service"
            mock_result.returncode = 1
            mock_subprocess.run.return_value = mock_result

            output = docker_service.compose_up("jarvis-auth")

        assert "failed" in output.lower()


# ---------------------------------------------------------------------------
# list_known_services
# ---------------------------------------------------------------------------


class TestListKnownServices:
    def test_returns_sorted_list(self, tmp_path: Path):
        for name in ("jarvis-tts", "jarvis-auth", "jarvis-logs"):
            d = tmp_path / name
            d.mkdir()
            (d / "docker-compose.yaml").touch()

        with patch.object(docker_service.config, "jarvis_root", str(tmp_path)):
            result = docker_service.list_known_services()

        names = [s["name"] for s in result]
        assert names == ["jarvis-auth", "jarvis-logs", "jarvis-tts"]
        assert all("path" in s for s in result)
