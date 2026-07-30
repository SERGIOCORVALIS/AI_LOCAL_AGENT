from packages.sandbox import SandboxRequest
from services.sandbox import SandboxExecutor


def test_sandbox_executor_runs_python_command() -> None:
    executor = SandboxExecutor()
    request = SandboxRequest(
        command=["python", "-c", "print('sandbox-ok')"],
        language="python",
    )

    result = executor.execute(request)

    assert result.success is True
    assert "sandbox-ok" in result.stdout
