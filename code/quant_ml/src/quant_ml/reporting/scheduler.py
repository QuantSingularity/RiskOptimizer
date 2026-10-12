import calendar
import datetime
import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, List, Optional

from quant_ml import settings
from quant_ml.reporting.delivery import EmailDelivery, validate_recipients
from quant_ml.reporting.generator import ReportGenerator
from quant_ml.reporting.template import ReportTemplate

logger = logging.getLogger(__name__)

FREQUENCIES = ("daily", "weekly", "monthly")


def ensure_within(path: str, base: str) -> str:
    resolved = os.path.realpath(path)
    root = os.path.realpath(base)
    if resolved != root and not resolved.startswith(root + os.sep):
        raise ValueError(f"Path must be inside {root}")
    return resolved


def add_months(value: datetime.datetime, months: int) -> datetime.datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class ReportScheduler:
    data_providers: Dict[str, Callable[[], Dict[str, Any]]] = {}

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        allow_external_paths: bool = False,
        delivery_handler: Optional[Callable[[str, List[str]], bool]] = None,
        use_environment_delivery: bool = True,
    ) -> None:
        self.storage_dir = str(storage_dir or (settings.report_dir() / "schedules"))
        os.makedirs(self.storage_dir, exist_ok=True)
        self.allow_external_paths = allow_external_paths
        if delivery_handler is None and use_environment_delivery:
            delivery_handler = EmailDelivery.from_environment()
        self.delivery_handler = delivery_handler
        self.schedules = self.load_schedules()

    @classmethod
    def register_data_provider(
        cls, name: str, provider: Callable[[], Dict[str, Any]]
    ) -> None:
        if not callable(provider) or not isinstance(name, str) or not name:
            raise ValueError("A provider name and a callable are required")
        cls.data_providers[name] = provider

    @property
    def schedule_file(self) -> str:
        return os.path.join(self.storage_dir, "schedules.json")

    def load_schedules(self) -> Dict[str, Any]:
        if not os.path.exists(self.schedule_file):
            return {}
        try:
            with open(self.schedule_file, encoding="utf-8") as handle:
                loaded = json.load(handle)
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError):
            logger.warning("Could not read schedules from %s", self.schedule_file)
            return {}

    def save_schedules(self) -> bool:
        try:
            temporary = f"{self.schedule_file}.tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(self.schedules, handle, indent=2)
            os.replace(temporary, self.schedule_file)
            return True
        except (OSError, TypeError, ValueError) as error:
            logger.error("Could not save schedules: %s", error)
            return False

    def check_path(self, path: str) -> str:
        if self.allow_external_paths:
            return os.path.abspath(path)
        return ensure_within(path, self.storage_dir)

    def add_schedule(
        self,
        name: str,
        template_path: str,
        output_path: str,
        frequency: str,
        data_provider: Optional[str] = None,
        recipients: Optional[List[str]] = None,
    ) -> Optional[str]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if frequency not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {', '.join(FREQUENCIES)}")
        if data_provider is not None and data_provider not in self.data_providers:
            raise ValueError(f"Unknown data provider: {data_provider}")
        schedule_id = str(uuid.uuid4())[:8]
        self.schedules[schedule_id] = {
            "name": name,
            "template_path": self.check_path(template_path),
            "output_path": self.check_path(output_path),
            "frequency": frequency,
            "data_provider": data_provider,
            "recipients": validate_recipients(list(recipients or [])),
            "last_run": None,
            "next_run": self.calculate_next_run(frequency),
            "created_at": datetime.datetime.now().isoformat(),
        }
        return schedule_id if self.save_schedules() else None

    def remove_schedule(self, schedule_id: str) -> bool:
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return self.save_schedules()
        return False

    def list_schedules(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": schedule_id,
                "name": schedule["name"],
                "frequency": schedule["frequency"],
                "last_run": schedule["last_run"],
                "next_run": schedule["next_run"],
            }
            for schedule_id, schedule in self.schedules.items()
        ]

    def run_scheduled_reports(self) -> Dict[str, Any]:
        now = datetime.datetime.now()
        results: Dict[str, Any] = {}
        for schedule_id, schedule in list(self.schedules.items()):
            if datetime.datetime.fromisoformat(schedule["next_run"]) <= now:
                results[schedule_id] = self.run_report(schedule_id)
                schedule["last_run"] = now.isoformat()
                schedule["next_run"] = self.calculate_next_run(
                    schedule["frequency"], now
                )
        self.save_schedules()
        return results

    def run_report(self, schedule_id: str) -> Dict[str, Any]:
        schedule = self.schedules.get(schedule_id)
        if schedule is None:
            return {"success": False, "error": "Schedule not found"}
        try:
            template = ReportTemplate.load(schedule["template_path"])
            if template is None:
                return {"success": False, "error": "Failed to load template"}
            data = None
            provider_name = schedule.get("data_provider")
            if provider_name:
                provider = self.data_providers.get(provider_name)
                if provider is None:
                    return {
                        "success": False,
                        "error": f"Data provider not registered: {provider_name}",
                    }
                try:
                    data = provider()
                except Exception as error:
                    return {"success": False, "error": f"Data provider failed: {error}"}
            generator = ReportGenerator(template)
            output_path = schedule["output_path"]
            if output_path.endswith(".pdf"):
                success = generator.generate_pdf(output_path, data)
            else:
                success = generator.generate_html(output_path, data)
            result: Dict[str, Any] = {"success": success, "output_path": output_path}
            if success and schedule["recipients"]:
                delivery = self.send_report(output_path, schedule["recipients"])
                result["delivered"] = delivery["delivered"]
                if not delivery["delivered"]:
                    result["delivery_error"] = delivery["error"]
            return result
        except Exception as error:
            logger.error("Scheduled report %s failed: %s", schedule_id, error)
            return {"success": False, "error": str(error)}

    @staticmethod
    def calculate_next_run(
        frequency: str, from_date: Optional[datetime.datetime] = None
    ) -> str:
        base = from_date or datetime.datetime.now()
        if frequency == "weekly":
            following = base + datetime.timedelta(days=7)
        elif frequency == "monthly":
            following = add_months(base, 1)
        else:
            following = base + datetime.timedelta(days=1)
        return following.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    def send_report(self, report_path: str, recipients: List[str]) -> Dict[str, Any]:
        if self.delivery_handler is None:
            logger.warning(
                "No delivery handler configured; report %s was not sent", report_path
            )
            return {"delivered": False, "error": "No delivery handler configured"}
        try:
            delivered = bool(self.delivery_handler(report_path, recipients))
        except Exception as error:
            logger.error("Report delivery failed: %s", error)
            return {"delivered": False, "error": str(error)}
        return {
            "delivered": delivered,
            "error": None if delivered else "Delivery handler returned false",
        }
