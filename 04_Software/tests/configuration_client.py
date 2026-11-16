"""HTTP test client that consumes durable configuration completion."""

from threading import RLock
import time

from adore.web.configuration import ConfigurationWorker
from fastapi.testclient import TestClient as HttpClient
import httpx

# One test-host consumer also coordinates concurrent clients/apps sharing the same home.
_WORKERS = {}
_WORKER_LOCK = RLock()


class TestClient(HttpClient):
    """Explicitly await accepted configuration through an offline in-process worker."""

    __test__ = False

    def request(self, *args, **kwargs):
        """Preserve response codes/bodies only after real durable confirmation."""
        response = super().request(*args, **kwargs)
        if response.status_code != 202:
            return response
        accepted = response.json()
        if accepted.get("domain") not in ("configuration_project", "configuration_global"):
            return response
        tasks = self.app.state.configuration_tasks
        identity = str(tasks.profiles.home.resolve())
        with _WORKER_LOCK:
            if identity not in _WORKERS:
                _WORKERS[identity] = [ConfigurationWorker(tasks), 0]
            shared = _WORKERS[identity]
            worker = shared[0]
            shared[1] += 1
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                with _WORKER_LOCK:
                    worker.tick()
                operation = worker.web.operation(accepted["id"])
                if operation["status"] not in ("pending", "running"):
                    outcome = worker.tasks.outcome(operation)
                    if outcome is None:
                        outcome = {
                            "status_code": 503,
                            "body": {
                                "detail": {"code": operation["reason"] or "configuration_failed"}
                            },
                        }
                    return httpx.Response(
                        outcome["status_code"], json=outcome["body"], request=response.request
                    )
                time.sleep(0.002)
            raise AssertionError("configuration operation exceeded the offline test budget")
        finally:
            with _WORKER_LOCK:
                shared[1] -= 1
                if shared[1] == 0:
                    worker.close()
                    del _WORKERS[identity]
