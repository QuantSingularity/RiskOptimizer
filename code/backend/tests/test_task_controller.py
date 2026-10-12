from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

TOKEN = {"Authorization": "Bearer test-token"}
BASE = "/api/v1/tasks"

SUBMISSIONS = [
    (
        "/risk/monte-carlo",
        "risk_tasks.monte_carlo_simulation",
        {"portfolio_data": {"AAA": 0.5, "BBB": 0.5}},
    ),
    (
        "/risk/var-cvar",
        "risk_tasks.calculate_var_cvar",
        {"portfolio_data": {"returns": [0.01, -0.02]}},
    ),
    (
        "/risk/efficient-frontier",
        "risk_tasks.efficient_frontier_calculation",
        {"assets_data": {"AAA": [1, 2]}},
    ),
    (
        "/risk/stress-test",
        "risk_tasks.stress_test_portfolio",
        {"portfolio_data": {"AAA": 1}, "stress_scenarios": [{"name": "crash"}]},
    ),
    (
        "/portfolio/optimize",
        "portfolio_tasks.optimize_portfolio",
        {"assets_data": {"AAA": [1, 2]}, "optimization_params": {"method": "x"}},
    ),
    (
        "/reports/portfolio",
        "report_tasks.generate_portfolio_report",
        {"portfolio_data": {"AAA": 1}, "report_config": {"format": "html"}},
    ),
]


@pytest.fixture
def client(make_client):
    return make_client("user")


@pytest.fixture
def admin(make_client):
    return make_client("admin")


def resolve(dotted):
    from src.api import task_controller

    module, name = dotted.split(".")
    return getattr(getattr(task_controller, module), name)


class TestSubmission:
    @pytest.mark.parametrize("path,target,body", SUBMISSIONS)
    def test_submit_returns_202_with_task_id(self, client, path, target, body):
        with patch.object(
            resolve(target), "delay", return_value=SimpleNamespace(id="abc")
        ):
            response = client.post(BASE + path, json=body, headers=TOKEN)
        assert response.status_code == 202
        data = response.get_json()["data"]
        assert data["task_id"] == "abc" and data["status"] == "PENDING"

    @pytest.mark.parametrize("path,target,body", SUBMISSIONS)
    def test_submit_requires_authentication(self, client, path, target, body):
        assert client.post(BASE + path, json=body).status_code == 401

    @pytest.mark.parametrize("path,target,body", SUBMISSIONS)
    def test_missing_fields_rejected(self, client, path, target, body):
        with patch.object(resolve(target), "delay") as delay:
            response = client.post(BASE + path, json={}, headers=TOKEN)
        assert response.status_code == 400
        delay.assert_not_called()

    def test_numeric_limits_enforced(self, client):
        target = resolve("risk_tasks.monte_carlo_simulation")
        with patch.object(target, "delay") as delay:
            for extra in (
                {"num_simulations": 10**9},
                {"time_horizon": 0},
                {"num_simulations": True},
            ):
                body = {"portfolio_data": {"AAA": 1}, **extra}
                assert (
                    client.post(
                        BASE + "/risk/monte-carlo", json=body, headers=TOKEN
                    ).status_code
                    == 400
                )
        delay.assert_not_called()

    def test_confidence_levels_validated(self, client):
        target = resolve("risk_tasks.calculate_var_cvar")
        with patch.object(target, "delay") as delay:
            response = client.post(
                BASE + "/risk/var-cvar",
                json={"portfolio_data": {"a": 1}, "confidence_levels": [1.5]},
                headers=TOKEN,
            )
        assert response.status_code == 400
        delay.assert_not_called()

    def test_broker_failure_is_500_not_401(self, client):
        target = resolve("risk_tasks.monte_carlo_simulation")
        with patch.object(target, "delay", side_effect=ConnectionError("down")):
            response = client.post(
                BASE + "/risk/monte-carlo",
                json={"portfolio_data": {"AAA": 1}},
                headers=TOKEN,
            )
        assert response.status_code == 500


class TestStatus:
    def make_result(self, ready, failed=False, successful=True):
        return MagicMock(
            status="SUCCESS" if successful else "FAILURE",
            result={"ok": True},
            info="boom",
            date_done=None,
            **{
                "ready.return_value": ready,
                "failed.return_value": failed,
                "successful.return_value": successful,
            },
        )

    def test_status(self, client):
        with patch(
            "src.api.task_controller.get_task_status",
            return_value=self.make_result(True),
        ), patch("src.api.task_controller.task_result_manager") as manager:
            manager.get_task_progress.return_value = {"percent": 100}
            manager.get_task_metadata.return_value = {}
            response = client.get(f"{BASE}/t1/status", headers=TOKEN)
        assert response.status_code == 200
        assert response.get_json()["data"]["result"] == {"ok": True}

    def test_result_pending_is_202(self, client):
        with patch(
            "src.api.task_controller.get_task_status",
            return_value=self.make_result(False),
        ):
            response = client.get(f"{BASE}/t1/result", headers=TOKEN)
        assert response.status_code == 202

    def test_result_failed_is_500(self, client):
        result = self.make_result(True, failed=True, successful=False)
        with patch("src.api.task_controller.get_task_status", return_value=result):
            response = client.get(f"{BASE}/t1/result", headers=TOKEN)
        assert response.status_code == 500

    def test_result_success(self, client):
        with patch(
            "src.api.task_controller.get_task_status",
            return_value=self.make_result(True),
        ):
            response = client.get(f"{BASE}/t1/result", headers=TOKEN)
        assert response.status_code == 200
        assert response.get_json()["data"]["result"] == {"ok": True}

    def test_cancel(self, client):
        with patch("src.api.task_controller.cancel_task") as cancel:
            response = client.delete(f"{BASE}/t1", headers=TOKEN)
        assert response.status_code == 200
        cancel.assert_called_once_with("t1")


class TestAdminOnly:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("post", "/maintenance/cleanup"),
            ("post", "/maintenance/health-check"),
            ("post", "/maintenance/cache-warmup"),
            ("get", "/active"),
            ("get", "/scheduled"),
            ("get", "/workers/stats"),
            ("get", "/queue/stats"),
        ],
    )
    def test_user_is_forbidden(self, client, method, path):
        assert getattr(client, method)(BASE + path, headers=TOKEN).status_code == 403

    def test_admin_can_start_maintenance(self, admin):
        target = resolve("maintenance_tasks.system_health_check")
        with patch.object(target, "delay", return_value=SimpleNamespace(id="m1")):
            response = admin.post(BASE + "/maintenance/health-check", headers=TOKEN)
        assert response.status_code == 202

    def test_queue_stats_degraded_threshold(self, admin):
        inspector = MagicMock()
        inspector.reserved.return_value = {"w": [1] * 1001}
        inspector.active.return_value = {"w": [1]}
        with patch("src.api.task_controller.celery_app") as app:
            app.control.inspect.return_value = inspector
            response = admin.get(BASE + "/queue/stats", headers=TOKEN)
        stats = response.get_json()["data"]["queue_stats"]
        assert stats["queue_health"] == "degraded"
        assert stats["total_queued_tasks"] == 1001
