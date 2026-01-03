"""
Deploy Skill for GatheRing.
Provides CI/CD and deployment operations for agents.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class DeploySkill(BaseSkill):
    """
    CI/CD and deployment operations skill.

    Provides tools for:
    - Docker container management
    - CI/CD pipeline execution
    - Environment management
    - Service deployment
    - Health checks and monitoring
    - Rollback operations
    """

    name = "deploy"
    description = "CI/CD and deployment operations"
    version = "1.0.0"
    required_permissions = [SkillPermission.DEPLOY, SkillPermission.EXECUTE]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir") if config else None
        self.docker_registry = config.get("docker_registry") if config else None
        self.environments = config.get("environments", ["dev", "staging", "production"]) if config else []

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "deploy_docker_build",
                "description": "Build a Docker image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to Dockerfile directory"},
                        "tag": {"type": "string", "description": "Image tag"},
                        "dockerfile": {"type": "string", "description": "Dockerfile name", "default": "Dockerfile"},
                        "build_args": {"type": "object", "description": "Build arguments"},
                        "no_cache": {"type": "boolean", "description": "Build without cache", "default": False}
                    },
                    "required": ["path", "tag"]
                }
            },
            {
                "name": "deploy_docker_push",
                "description": "Push Docker image to registry",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "description": "Image name with tag"},
                        "registry": {"type": "string", "description": "Registry URL (optional)"}
                    },
                    "required": ["image"]
                }
            },
            {
                "name": "deploy_docker_run",
                "description": "Run a Docker container",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "description": "Image to run"},
                        "name": {"type": "string", "description": "Container name"},
                        "ports": {"type": "array", "items": {"type": "string"}, "description": "Port mappings (e.g., '8080:80')"},
                        "env": {"type": "object", "description": "Environment variables"},
                        "volumes": {"type": "array", "items": {"type": "string"}, "description": "Volume mounts"},
                        "detach": {"type": "boolean", "description": "Run in background", "default": True},
                        "network": {"type": "string", "description": "Network to connect to"}
                    },
                    "required": ["image"]
                }
            },
            {
                "name": "deploy_docker_compose",
                "description": "Run docker-compose commands",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to docker-compose.yml"},
                        "action": {
                            "type": "string",
                            "enum": ["up", "down", "restart", "logs", "ps", "build"],
                            "description": "Compose action"
                        },
                        "services": {"type": "array", "items": {"type": "string"}, "description": "Specific services"},
                        "detach": {"type": "boolean", "description": "Run in background (for up)", "default": True}
                    },
                    "required": ["path", "action"]
                }
            },
            {
                "name": "deploy_status",
                "description": "Get deployment status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "environment": {"type": "string", "description": "Environment name"},
                        "service": {"type": "string", "description": "Service name (optional)"}
                    },
                    "required": ["environment"]
                }
            },
            {
                "name": "deploy_health_check",
                "description": "Run health checks on deployed services",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Health check URL"},
                        "expected_status": {"type": "integer", "description": "Expected HTTP status", "default": 200},
                        "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                        "retries": {"type": "integer", "description": "Number of retries", "default": 3}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "deploy_rollback",
                "description": "Rollback to a previous deployment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "environment": {"type": "string", "description": "Environment name"},
                        "service": {"type": "string", "description": "Service name"},
                        "version": {"type": "string", "description": "Version to rollback to"}
                    },
                    "required": ["environment", "service"]
                }
            },
            {
                "name": "deploy_env_config",
                "description": "Manage environment configuration",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "get", "set", "delete"],
                            "description": "Config action"
                        },
                        "environment": {"type": "string", "description": "Environment name"},
                        "key": {"type": "string", "description": "Config key"},
                        "value": {"type": "string", "description": "Config value (for set)"}
                    },
                    "required": ["action", "environment"]
                }
            },
            {
                "name": "deploy_ci_trigger",
                "description": "Trigger CI/CD pipeline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["github", "gitlab", "jenkins", "circleci"],
                            "description": "CI provider"
                        },
                        "repo": {"type": "string", "description": "Repository"},
                        "branch": {"type": "string", "description": "Branch to build", "default": "main"},
                        "workflow": {"type": "string", "description": "Workflow/pipeline name"}
                    },
                    "required": ["provider", "repo"]
                }
            },
            {
                "name": "deploy_logs",
                "description": "Get deployment/container logs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "container": {"type": "string", "description": "Container name or ID"},
                        "lines": {"type": "integer", "description": "Number of lines", "default": 100},
                        "follow": {"type": "boolean", "description": "Follow log output", "default": False},
                        "since": {"type": "string", "description": "Show logs since timestamp"}
                    },
                    "required": ["container"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a deployment tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "deploy_docker_build": self._docker_build,
                "deploy_docker_push": self._docker_push,
                "deploy_docker_run": self._docker_run,
                "deploy_docker_compose": self._docker_compose,
                "deploy_status": self._deploy_status,
                "deploy_health_check": self._health_check,
                "deploy_rollback": self._rollback,
                "deploy_env_config": self._env_config,
                "deploy_ci_trigger": self._ci_trigger,
                "deploy_logs": self._deploy_logs,
            }

            if tool_name not in handlers:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            result = handlers[tool_name](tool_input)
            result.skill_name = self.name
            result.tool_name = tool_name
            result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return result

        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    def _check_docker(self) -> Optional[SkillResponse]:
        """Check if Docker is available."""
        try:
            subprocess.run(["docker", "version"], capture_output=True, check=True)
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            return SkillResponse(
                success=False,
                message="Docker not available",
                error="docker_not_found"
            )

    def _docker_build(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Build Docker image."""
        docker_error = self._check_docker()
        if docker_error:
            return docker_error

        path = Path(tool_input["path"]).resolve()
        tag = tool_input["tag"]
        dockerfile = tool_input.get("dockerfile", "Dockerfile")
        build_args = tool_input.get("build_args", {})
        no_cache = tool_input.get("no_cache", False)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        dockerfile_path = path / dockerfile
        if not dockerfile_path.exists():
            return SkillResponse(success=False, message=f"Dockerfile not found: {dockerfile_path}", error="dockerfile_not_found")

        # Build command
        cmd = ["docker", "build", "-t", tag, "-f", str(dockerfile_path)]

        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

        if no_cache:
            cmd.append("--no-cache")

        cmd.append(str(path))

        return SkillResponse(
            success=True,
            message=f"Ready to build Docker image: {tag}",
            needs_confirmation=True,
            confirmation_type="execute",
            confirmation_message=f"Build Docker image '{tag}'?",
            data={
                "command": " ".join(cmd),
                "tag": tag,
                "dockerfile": str(dockerfile_path),
                "build_args": build_args,
            }
        )

    def _docker_push(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Push Docker image."""
        docker_error = self._check_docker()
        if docker_error:
            return docker_error

        image = tool_input["image"]
        registry = tool_input.get("registry") or self.docker_registry

        # Full image name with registry
        if registry and not image.startswith(registry):
            full_image = f"{registry}/{image}"
        else:
            full_image = image

        return SkillResponse(
            success=True,
            message=f"Ready to push Docker image: {full_image}",
            needs_confirmation=True,
            confirmation_type="execute",
            confirmation_message=f"Push image '{full_image}' to registry?",
            data={
                "command": f"docker push {full_image}",
                "image": full_image,
                "registry": registry,
            }
        )

    def _docker_run(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run Docker container."""
        docker_error = self._check_docker()
        if docker_error:
            return docker_error

        image = tool_input["image"]
        name = tool_input.get("name")
        ports = tool_input.get("ports", [])
        env = tool_input.get("env", {})
        volumes = tool_input.get("volumes", [])
        detach = tool_input.get("detach", True)
        network = tool_input.get("network")

        cmd = ["docker", "run"]

        if detach:
            cmd.append("-d")

        if name:
            cmd.extend(["--name", name])

        for port in ports:
            cmd.extend(["-p", port])

        for key, value in env.items():
            cmd.extend(["-e", f"{key}={value}"])

        for volume in volumes:
            cmd.extend(["-v", volume])

        if network:
            cmd.extend(["--network", network])

        cmd.append(image)

        return SkillResponse(
            success=True,
            message=f"Ready to run container: {image}",
            needs_confirmation=True,
            confirmation_type="execute",
            confirmation_message=f"Run container from image '{image}'?",
            data={
                "command": " ".join(cmd),
                "image": image,
                "name": name,
                "ports": ports,
                "detach": detach,
            }
        )

    def _docker_compose(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run docker-compose commands."""
        docker_error = self._check_docker()
        if docker_error:
            return docker_error

        path = Path(tool_input["path"]).resolve()
        action = tool_input["action"]
        services = tool_input.get("services", [])
        detach = tool_input.get("detach", True)

        if not path.exists():
            return SkillResponse(success=False, message=f"Path not found: {path}", error="not_found")

        # Determine compose command (docker-compose or docker compose)
        try:
            subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
            compose_cmd = ["docker", "compose"]
        except subprocess.CalledProcessError:
            compose_cmd = ["docker-compose"]

        cmd = compose_cmd + ["-f", str(path)]

        if action == "up":
            cmd.append("up")
            if detach:
                cmd.append("-d")
        elif action == "down":
            cmd.append("down")
        elif action == "restart":
            cmd.append("restart")
        elif action == "logs":
            cmd.extend(["logs", "--tail", "100"])
        elif action == "ps":
            cmd.append("ps")
        elif action == "build":
            cmd.append("build")

        if services:
            cmd.extend(services)

        # For destructive actions, require confirmation
        if action in ("down", "restart"):
            return SkillResponse(
                success=True,
                message=f"Ready to {action} services",
                needs_confirmation=True,
                confirmation_type="destructive" if action == "down" else "execute",
                confirmation_message=f"Run 'docker-compose {action}'?",
                data={
                    "command": " ".join(cmd),
                    "action": action,
                    "services": services,
                }
            )

        # For non-destructive, execute directly
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return SkillResponse(
                success=result.returncode == 0,
                message=f"docker-compose {action} completed",
                data={
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None,
                    "command": " ".join(cmd),
                }
            )
        except subprocess.TimeoutExpired:
            return SkillResponse(success=False, message="Command timed out", error="timeout")

    def _deploy_status(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get deployment status."""
        environment = tool_input["environment"]
        service = tool_input.get("service")

        # Get running containers
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True
            )

            containers = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # Filter by environment/service if provided
            if service:
                containers = [c for c in containers if service in c.get("Names", "")]

            return SkillResponse(
                success=True,
                message=f"Found {len(containers)} running containers",
                data={
                    "environment": environment,
                    "service": service,
                    "containers": containers,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        except FileNotFoundError:
            return SkillResponse(
                success=False,
                message="Docker not available",
                error="docker_not_found"
            )

    def _health_check(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Run health check."""
        url = tool_input["url"]
        expected_status = tool_input.get("expected_status", 200)
        timeout = tool_input.get("timeout", 30)
        retries = tool_input.get("retries", 3)

        import urllib.request
        import urllib.error

        for attempt in range(retries):
            try:
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    status = response.getcode()
                    body = response.read().decode("utf-8")[:500]

                    if status == expected_status:
                        return SkillResponse(
                            success=True,
                            message=f"Health check passed (HTTP {status})",
                            data={
                                "url": url,
                                "status": status,
                                "attempt": attempt + 1,
                                "response_preview": body,
                            }
                        )
                    else:
                        return SkillResponse(
                            success=False,
                            message=f"Unexpected status: {status} (expected {expected_status})",
                            data={
                                "url": url,
                                "status": status,
                                "expected": expected_status,
                            }
                        )

            except urllib.error.URLError as e:
                if attempt < retries - 1:
                    continue
                return SkillResponse(
                    success=False,
                    message=f"Health check failed: {str(e)}",
                    error="connection_error",
                    data={
                        "url": url,
                        "attempts": retries,
                        "error": str(e),
                    }
                )
            except Exception as e:
                return SkillResponse(
                    success=False,
                    message=f"Health check error: {str(e)}",
                    error=str(e)
                )

        return SkillResponse(
            success=False,
            message=f"Health check failed after {retries} attempts",
            error="max_retries"
        )

    def _rollback(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Rollback deployment."""
        environment = tool_input["environment"]
        service = tool_input["service"]
        version = tool_input.get("version")

        return SkillResponse(
            success=True,
            message=f"Ready to rollback {service} in {environment}",
            needs_confirmation=True,
            confirmation_type="destructive",
            confirmation_message=f"Rollback {service} to {version or 'previous version'} in {environment}?",
            data={
                "environment": environment,
                "service": service,
                "version": version,
                "note": "Implement rollback logic based on your deployment strategy",
            }
        )

    def _env_config(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Manage environment configuration."""
        action = tool_input["action"]
        environment = tool_input["environment"]
        key = tool_input.get("key")
        value = tool_input.get("value")

        # Config file path
        config_dir = Path(self.working_dir or ".") / "config" / environment
        config_file = config_dir / ".env"

        if action == "list":
            if not config_file.exists():
                return SkillResponse(
                    success=True,
                    message=f"No config found for {environment}",
                    data={"environment": environment, "config": {}}
                )

            config = {}
            with open(config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        # Mask sensitive values
                        if any(s in k.lower() for s in ["password", "secret", "key", "token"]):
                            v = "***"
                        config[k] = v

            return SkillResponse(
                success=True,
                message=f"Config for {environment}",
                data={"environment": environment, "config": config}
            )

        elif action == "get":
            if not key:
                return SkillResponse(success=False, message="Key required for get", error="missing_key")

            if not config_file.exists():
                return SkillResponse(success=False, message=f"Config not found: {environment}", error="not_found")

            with open(config_file, "r") as f:
                for line in f:
                    if line.strip().startswith(f"{key}="):
                        _, v = line.strip().split("=", 1)
                        return SkillResponse(
                            success=True,
                            message=f"Config value for {key}",
                            data={"key": key, "value": v, "environment": environment}
                        )

            return SkillResponse(success=False, message=f"Key not found: {key}", error="key_not_found")

        elif action == "set":
            if not key or value is None:
                return SkillResponse(success=False, message="Key and value required for set", error="missing_params")

            return SkillResponse(
                success=True,
                message=f"Ready to set {key} in {environment}",
                needs_confirmation=True,
                confirmation_type="write_file",
                confirmation_message=f"Set {key}={value[:20]}... in {environment}?",
                data={
                    "environment": environment,
                    "key": key,
                    "value": value,
                    "config_file": str(config_file),
                }
            )

        elif action == "delete":
            if not key:
                return SkillResponse(success=False, message="Key required for delete", error="missing_key")

            return SkillResponse(
                success=True,
                message=f"Ready to delete {key} from {environment}",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Delete {key} from {environment} config?",
                data={
                    "environment": environment,
                    "key": key,
                    "config_file": str(config_file),
                }
            )

        return SkillResponse(success=False, message=f"Unknown action: {action}", error="unknown_action")

    def _ci_trigger(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Trigger CI/CD pipeline."""
        provider = tool_input["provider"]
        repo = tool_input["repo"]
        branch = tool_input.get("branch", "main")
        workflow = tool_input.get("workflow")

        if provider == "github":
            # Use gh CLI
            cmd = ["gh", "workflow", "run"]
            if workflow:
                cmd.append(workflow)
            cmd.extend(["--repo", repo, "--ref", branch])

            return SkillResponse(
                success=True,
                message="Ready to trigger GitHub Actions workflow",
                needs_confirmation=True,
                confirmation_type="execute",
                confirmation_message=f"Trigger workflow on {repo}:{branch}?",
                data={
                    "command": " ".join(cmd),
                    "provider": provider,
                    "repo": repo,
                    "branch": branch,
                    "workflow": workflow,
                }
            )

        elif provider == "gitlab":
            return SkillResponse(
                success=True,
                message="GitLab CI trigger ready",
                needs_confirmation=True,
                confirmation_type="execute",
                confirmation_message=f"Trigger GitLab CI pipeline on {repo}:{branch}?",
                data={
                    "provider": provider,
                    "repo": repo,
                    "branch": branch,
                    "api_endpoint": f"/projects/{repo}/pipeline",
                    "note": "Requires GITLAB_TOKEN environment variable",
                }
            )

        return SkillResponse(
            success=False,
            message=f"Provider not fully implemented: {provider}",
            error="not_implemented",
            data={
                "provider": provider,
                "supported": ["github", "gitlab"],
            }
        )

    def _deploy_logs(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get container logs."""
        docker_error = self._check_docker()
        if docker_error:
            return docker_error

        container = tool_input["container"]
        lines = tool_input.get("lines", 100)
        follow = tool_input.get("follow", False)
        since = tool_input.get("since")

        cmd = ["docker", "logs", "--tail", str(lines)]

        if since:
            cmd.extend(["--since", since])

        cmd.append(container)

        if follow:
            return SkillResponse(
                success=True,
                message=f"Ready to follow logs for {container}",
                needs_confirmation=True,
                confirmation_type="long_running",
                confirmation_message=f"Follow logs for {container}? (Press Ctrl+C to stop)",
                data={
                    "command": " ".join(cmd + ["-f"]),
                    "container": container,
                }
            )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return SkillResponse(
                success=result.returncode == 0,
                message=f"Logs for {container}",
                data={
                    "logs": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None,
                    "container": container,
                    "lines": lines,
                }
            )
        except subprocess.TimeoutExpired:
            return SkillResponse(success=False, message="Log retrieval timed out", error="timeout")
