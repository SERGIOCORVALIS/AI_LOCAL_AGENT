from pytest import MonkeyPatch

from packages.sandbox import SandboxExecution, SandboxRequest
from services.sandbox import SandboxExecutor


def test_sandbox_executor_runs_python_command() -> None:
    executor = SandboxExecutor(prefer_docker=False)
    request = SandboxRequest(
        command=["python", "-c", "print('sandbox-ok')"],
        language="python",
    )

    result = executor.execute(request)

    assert result.success is True
    assert "sandbox-ok" in result.stdout
    assert result.mode == "local"
    assert result.isolated is False


def test_sandbox_prefer_docker_falls_back_locally(monkeypatch: MonkeyPatch) -> None:
    executor = SandboxExecutor(prefer_docker=True)
    monkeypatch.setattr(executor, "_docker_available", lambda: False)
    result = executor.execute(
        SandboxRequest(
            command=["python", "-c", "print('fallback-ok')"],
            language="python",
        )
    )
    assert result.success is True
    assert "fallback-ok" in result.stdout
    assert result.degraded is True
    assert "docker_unavailable" in result.stderr


def test_sandbox_uses_docker_when_available(monkeypatch: MonkeyPatch) -> None:
    executor = SandboxExecutor(prefer_docker=True)
    monkeypatch.setattr(executor, "_docker_available", lambda: True)

    def fake_docker(request: SandboxRequest) -> SandboxExecution:
        del request
        return SandboxExecution(
            success=True,
            stdout="docker-ok\n",
            stderr="",
            exit_code=0,
            mode="docker",
            isolated=True,
        )

    called = {"local": False}

    def fake_local(request: SandboxRequest) -> SandboxExecution:
        called["local"] = True
        del request
        return SandboxExecution(success=True, stdout="local\n", stderr="", exit_code=0)

    monkeypatch.setattr(executor, "_execute_docker", fake_docker)
    monkeypatch.setattr(executor, "_execute_local", fake_local)
    result = executor.execute(
        SandboxRequest(command=["python", "-c", "print(1)"], language="python")
    )
    assert result.success is True
    assert "docker-ok" in result.stdout
    assert result.mode == "docker"
    assert called["local"] is False
