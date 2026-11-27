"""Shared test setup.

A runtime ``Workspace`` checks the Docker sandbox in a background thread that every workspace of the process shares
(``nodestro_runtime.docker_status.monitor_for``). With a Docker daemon (CI runners have one), that check outlives
the test that created the workspace: its self-test resolves Nodestro's runtime image with ``uv pip compile`` in a
``nodestro-resolve-*`` temporary directory and builds the image. Created during a later test, that directory lands in
the later test's temporary root and its leak check (rightly) finds a directory nobody of that test made. None of
these tests needs Docker, so every test gets the runtime's fixed stand-in monitor, as the runtime's own tests do:
no thread, no docker CLI, no reaper.
"""

from __future__ import annotations

from nodestro_runtime import docker_status
from nodestro_runtime.testing import StaticDockerMonitor
import pytest


@pytest.fixture(autouse=True)
def _no_docker_check(monkeypatch: pytest.MonkeyPatch) -> None:
    docker_status.reset_monitors()
    monkeypatch.setattr(docker_status, "monitor_for", lambda *args, **kwargs: StaticDockerMonitor())
