import datetime
import difflib
import json
import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional

import settings
from reporting.scheduler import ensure_within

logger = logging.getLogger(__name__)

REPORT_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")
MAX_READ_BYTES = 5_000_000


class ReportArchive:
    def __init__(self, archive_dir: Optional[str] = None) -> None:
        self.archive_dir = str(archive_dir or (settings.report_dir() / "archive"))
        os.makedirs(self.archive_dir, exist_ok=True)

    def type_dir(self, report_type: str) -> str:
        if not isinstance(report_type, str) or not REPORT_TYPE_PATTERN.match(
            report_type
        ):
            raise ValueError(
                "report_type may only contain letters, digits, underscores and hyphens"
            )
        return os.path.join(self.archive_dir, report_type)

    def archive_report(
        self,
        report_path: str,
        report_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        directory = self.type_dir(report_type)
        if not os.path.isfile(report_path):
            logger.error("Report file not found: %s", report_path)
            return None
        os.makedirs(directory, exist_ok=True)
        base_name, extension = os.path.splitext(os.path.basename(report_path))
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        archive_path = os.path.join(directory, f"{base_name}_{timestamp}{extension}")
        try:
            shutil.copy2(report_path, archive_path)
            if metadata:
                with open(archive_path + ".meta", "w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, indent=2)
            return archive_path
        except (OSError, TypeError, ValueError) as error:
            logger.error("Error archiving report: %s", error)
            return None

    def list_archived_reports(
        self, report_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        reports: List[Dict[str, Any]] = []
        if report_type:
            directory = self.type_dir(report_type)
            if os.path.isdir(directory):
                reports.extend(self.list_directory(directory, report_type))
        else:
            for name in os.listdir(self.archive_dir):
                directory = os.path.join(self.archive_dir, name)
                if os.path.isdir(directory):
                    reports.extend(self.list_directory(directory, name))
        reports.sort(key=lambda item: item["timestamp"], reverse=True)
        return reports[:limit]

    def list_directory(self, directory: str, report_type: str) -> List[Dict[str, Any]]:
        reports = []
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            if filename.endswith(".meta") or not os.path.isfile(path):
                continue
            timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            metadata: Dict[str, Any] = {}
            meta_path = path + ".meta"
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, encoding="utf-8") as handle:
                        metadata = json.load(handle)
                except (OSError, ValueError):
                    metadata = {}
            reports.append(
                {
                    "path": path,
                    "filename": filename,
                    "report_type": report_type,
                    "timestamp": timestamp,
                    "metadata": metadata,
                }
            )
        return reports

    def read_text(self, report_path: str) -> str:
        resolved = ensure_within(report_path, self.archive_dir)
        if os.path.getsize(resolved) > MAX_READ_BYTES:
            raise ValueError("Report is too large to read")
        with open(resolved, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def get_report(self, report_path: str) -> Optional[str]:
        try:
            return self.read_text(report_path)
        except (OSError, ValueError) as error:
            logger.error("Error reading report: %s", error)
            return None

    def compare_reports(self, report_path1: str, report_path2: str) -> Optional[str]:
        try:
            first = self.read_text(report_path1)
            second = self.read_text(report_path2)
        except (OSError, ValueError) as error:
            logger.error("Error comparing reports: %s", error)
            return None
        diff = difflib.unified_diff(
            first.splitlines(),
            second.splitlines(),
            fromfile=os.path.basename(report_path1),
            tofile=os.path.basename(report_path2),
            lineterm="",
        )
        return "\n".join(diff)
