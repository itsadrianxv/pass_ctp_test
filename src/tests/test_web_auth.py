import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch

from src.config import reader as config_reader
import src.logging as logging_module
import src.web.process_manager as process_manager_module
import src.web.rpc_client as rpc_client_module


def _load_app_module():
    sys.modules.pop("src.web.app", None)

    with (
        patch.object(config_reader, "get_web_secret_key", return_value="test-secret"),
        patch.object(logging_module, "setup_logger"),
        patch.object(process_manager_module, "ProcessManager", return_value=MagicMock()),
        patch.object(rpc_client_module, "RpcClient", return_value=MagicMock()),
    ):
        return importlib.import_module("src.web.app")


class WebAuthTests(unittest.TestCase):
    def test_api_requires_login(self):
        app_module = _load_app_module()
        client = app_module.app.test_client()

        response = client.post("/api/worker/kill")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"status": "error", "msg": "authentication_required"})

    def test_logged_in_session_can_access_protected_api(self):
        app_module = _load_app_module()
        client = app_module.app.test_client()

        with client.session_transaction() as flask_session:
            flask_session["logged_in"] = True

        response = client.post("/api/worker/kill")

        self.assertEqual(response.status_code, 200)

    def test_worker_status_returns_json_when_rpc_times_out(self):
        app_module = _load_app_module()
        app_module.rpc.request.side_effect = TimeoutError("timed out")
        client = app_module.app.test_client()

        with client.session_transaction() as flask_session:
            flask_session["logged_in"] = True

        response = client.get("/api/worker/status")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {"status": "error", "msg": "Worker RPC 请求超时，请稍后重试"},
        )


if __name__ == "__main__":
    unittest.main()
