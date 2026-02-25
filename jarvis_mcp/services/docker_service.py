"""Docker container management service.

Provides operations for listing, inspecting, and managing Docker containers
and compose stacks. All operations are restricted to jarvis-related containers.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any

import docker
from docker.models.containers import Container

from jarvis_mcp.config import config

logger = logging.getLogger(__name__)

_COMPOSE_TIMEOUT_SECONDS = 120

# Known infrastructure container names that are part of the jarvis ecosystem
_KNOWN_INFRA_NAMES = frozenset({
    "loki",
    "grafana",
    "mosquitto",
    "minio",
    "postgres",
    "redis",
})

# Compose file names to search for
_COMPOSE_FILENAMES = (
    "docker-compose.yaml",
    "docker-compose.yml",
    "compose.yaml",
    "compose.yml",
)


def _get_client() -> docker.DockerClient:
    """Get a Docker client connected to the local daemon."""
    return docker.from_env()


def _is_jarvis_container(container: Container) -> bool:
    """Check if a container belongs to the jarvis ecosystem.

    A container is considered jarvis-related if:
    - Its name contains "jarvis", OR
    - It has a com.docker.compose.project label containing "jarvis", OR
    - Its name matches a known infrastructure service name
    """
    name: str = container.name or ""
    if "jarvis" in name.lower():
        return True

    labels: dict[str, str] = container.labels or {}
    project: str = labels.get("com.docker.compose.project", "")
    if "jarvis" in project.lower():
        return True

    # Check known infra names (exact match on the base name)
    base_name: str = name.lower().split("-")[-1] if "-" in name else name.lower()
    if base_name in _KNOWN_INFRA_NAMES:
        return True

    return False


def _find_jarvis_container(name: str) -> Container:
    """Find a single jarvis container by partial name match.

    Uses exact-first priority: if the name matches a container name exactly,
    that container is returned. Otherwise, partial substring matching is used.

    Raises:
        ValueError: If no matching container is found or if the match is ambiguous.
    """
    client = _get_client()
    all_containers: list[Container] = client.containers.list(all=True)
    jarvis_containers: list[Container] = [c for c in all_containers if _is_jarvis_container(c)]

    search: str = name.lower()

    # Exact match first
    for c in jarvis_containers:
        if (c.name or "").lower() == search:
            return c

    # Partial match
    matches: list[Container] = [
        c for c in jarvis_containers if search in (c.name or "").lower()
    ]

    if len(matches) == 0:
        available: list[str] = sorted(c.name or "" for c in jarvis_containers)
        raise ValueError(
            f"No jarvis container matching '{name}'. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    if len(matches) > 1:
        names: list[str] = sorted(c.name or "" for c in matches)
        raise ValueError(
            f"Ambiguous match for '{name}': {', '.join(names)}. "
            f"Be more specific."
        )

    return matches[0]


def list_containers(show_all: bool = False) -> list[dict[str, Any]]:
    """List jarvis-related containers.

    Args:
        show_all: If True, include stopped containers. Default shows only running.

    Returns:
        List of container info dicts.
    """
    client = _get_client()
    all_containers: list[Container] = client.containers.list(all=show_all)
    jarvis_containers: list[Container] = [c for c in all_containers if _is_jarvis_container(c)]

    result: list[dict[str, Any]] = []
    for c in sorted(jarvis_containers, key=lambda x: x.name or ""):
        ports: dict[str, Any] = c.ports or {}
        port_strings: list[str] = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port: str = binding.get("HostPort", "?")
                    port_strings.append(f"{host_port}->{container_port}")
            else:
                port_strings.append(container_port)

        result.append({
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image and c.image.tags else str(c.image.id)[:12] if c.image else "unknown",
            "ports": ", ".join(port_strings) if port_strings else "",
        })

    return result


def get_container_logs(
    name: str,
    lines: int = 100,
    since: str | None = None,
) -> str:
    """Get recent logs from a jarvis container.

    Args:
        name: Container name (partial match supported).
        lines: Number of tail lines to return.
        since: Only return logs since this timestamp (e.g., "1h", "30m", "2024-01-01").

    Returns:
        Log text from the container.
    """
    container: Container = _find_jarvis_container(name)

    kwargs: dict[str, Any] = {
        "tail": min(lines, 1000),
        "timestamps": True,
    }
    if since:
        kwargs["since"] = since

    logs: bytes = container.logs(**kwargs)
    return logs.decode("utf-8", errors="replace")


def restart_container(name: str) -> str:
    """Restart a jarvis container.

    Args:
        name: Container name (partial match supported).

    Returns:
        Status message.
    """
    container: Container = _find_jarvis_container(name)
    container_name: str = container.name or name
    container.restart(timeout=30)
    return f"Container '{container_name}' restarted successfully."


def stop_container(name: str) -> str:
    """Stop a running jarvis container.

    Args:
        name: Container name (partial match supported).

    Returns:
        Status message.
    """
    container: Container = _find_jarvis_container(name)
    container_name: str = container.name or name
    if container.status != "running":
        return f"Container '{container_name}' is already {container.status}."
    container.stop(timeout=30)
    return f"Container '{container_name}' stopped successfully."


def start_container(name: str) -> str:
    """Start a stopped jarvis container.

    Args:
        name: Container name (partial match supported).

    Returns:
        Status message.
    """
    container: Container = _find_jarvis_container(name)
    container_name: str = container.name or name
    if container.status == "running":
        return f"Container '{container_name}' is already running."
    container.start()
    return f"Container '{container_name}' started successfully."


def _discover_service_dirs() -> dict[str, Path]:
    """Discover jarvis service directories that have compose files.

    Scans JARVIS_ROOT/jarvis-*/ for directories containing docker-compose files.

    Returns:
        Dict mapping service name to directory path.
    """
    root = Path(config.jarvis_root)
    if not root.is_dir():
        logger.warning("JARVIS_ROOT does not exist: %s", root)
        return {}

    services: dict[str, Path] = {}
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not child.name.startswith("jarvis-"):
            continue

        for compose_name in _COMPOSE_FILENAMES:
            if (child / compose_name).is_file():
                services[child.name] = child
                break

    return services


def compose_up(service: str) -> str:
    """Run `docker compose up -d` for a jarvis service.

    Args:
        service: Service directory name (e.g., "jarvis-auth" or "auth").

    Returns:
        Command output.

    Raises:
        ValueError: If the service is not found.
    """
    service_dir: Path = _resolve_service_dir(service)
    return _run_compose(service_dir, ["up", "-d"])


def compose_down(service: str) -> str:
    """Run `docker compose down` for a jarvis service.

    Args:
        service: Service directory name (e.g., "jarvis-auth" or "auth").

    Returns:
        Command output.

    Raises:
        ValueError: If the service is not found.
    """
    service_dir: Path = _resolve_service_dir(service)
    return _run_compose(service_dir, ["down"])


def list_known_services() -> list[dict[str, str]]:
    """List jarvis services that have compose files.

    Returns:
        Sorted list of dicts with 'name' and 'path' keys.
    """
    services = _discover_service_dirs()
    return [
        {"name": name, "path": str(path)}
        for name, path in sorted(services.items())
    ]


def _resolve_service_dir(service: str) -> Path:
    """Resolve a service name to its directory path.

    Accepts both "jarvis-auth" and "auth" forms.

    Raises:
        ValueError: If the service directory is not found or has no compose file.
    """
    services = _discover_service_dirs()

    # Try exact match first
    if service in services:
        return services[service]

    # Try with jarvis- prefix
    prefixed: str = f"jarvis-{service}" if not service.startswith("jarvis-") else service
    if prefixed in services:
        return services[prefixed]

    available: list[str] = sorted(services.keys())
    raise ValueError(
        f"No compose file found for '{service}'. "
        f"Available: {', '.join(available) if available else '(none)'}"
    )


def _run_compose(service_dir: Path, args: list[str]) -> str:
    """Run a docker compose command in a service directory.

    Args:
        service_dir: Path to the service directory.
        args: Arguments to pass after `docker compose`.

    Returns:
        Combined stdout + stderr output.
    """
    cmd: list[str] = ["docker", "compose", *args]
    logger.info("Running: %s in %s", " ".join(cmd), service_dir)

    result: subprocess.CompletedProcess[str] = subprocess.run(
        cmd,
        cwd=str(service_dir),
        capture_output=True,
        text=True,
        timeout=_COMPOSE_TIMEOUT_SECONDS,
    )

    output: str = result.stdout
    if result.stderr:
        output += "\n" + result.stderr if output else result.stderr

    if result.returncode != 0:
        return f"Command failed (exit {result.returncode}):\n{output}"

    return output.strip() if output.strip() else f"docker compose {' '.join(args)} completed successfully."
