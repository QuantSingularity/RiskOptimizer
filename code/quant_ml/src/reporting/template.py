import datetime
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SECTION_TYPES = ("text", "chart", "table")
MAX_SECTIONS = 200


def now_iso() -> str:
    return datetime.datetime.now().isoformat()


def validate_section_type(section_type: Any) -> str:
    if section_type not in SECTION_TYPES:
        raise ValueError(f"section type must be one of {', '.join(SECTION_TYPES)}")
    return section_type


class ReportTemplate:
    def __init__(
        self,
        title: str,
        sections: Optional[List[Dict[str, Any]]] = None,
        description: str = "",
        author: str = "",
        version: str = "1.0",
    ) -> None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        self.id = str(uuid.uuid4())[:8]
        self.title = title
        self.sections: List[Dict[str, Any]] = []
        for section in sections or []:
            if not isinstance(section, dict):
                raise ValueError("sections must be objects")
            normalised = dict(section)
            normalised.setdefault("id", str(uuid.uuid4())[:8])
            normalised.setdefault("title", "")
            normalised.setdefault("content", "")
            normalised["type"] = validate_section_type(normalised.get("type", "text"))
            self.sections.append(normalised)
        if len(self.sections) > MAX_SECTIONS:
            raise ValueError(f"A template supports at most {MAX_SECTIONS} sections")
        self.description = description
        self.author = author
        self.version = version
        self.created_at = now_iso()
        self.updated_at = self.created_at

    def add_section(
        self,
        title: str,
        content: Any = "",
        section_type: str = "text",
        position: Optional[int] = None,
    ) -> "ReportTemplate":
        if len(self.sections) >= MAX_SECTIONS:
            raise ValueError(f"A template supports at most {MAX_SECTIONS} sections")
        section = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "type": validate_section_type(section_type),
        }
        if position is None:
            self.sections.append(section)
        else:
            self.sections.insert(position, section)
        self.updated_at = now_iso()
        return self

    def update_section(
        self,
        section_id: str,
        title: Optional[str] = None,
        content: Any = None,
        section_type: Optional[str] = None,
    ) -> bool:
        for section in self.sections:
            if section["id"] == section_id:
                if title is not None:
                    section["title"] = title
                if content is not None:
                    section["content"] = content
                if section_type is not None:
                    section["type"] = validate_section_type(section_type)
                self.updated_at = now_iso()
                return True
        return False

    def remove_section(self, section_id: str) -> bool:
        for index, section in enumerate(self.sections):
            if section["id"] == section_id:
                self.sections.pop(index)
                self.updated_at = now_iso()
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "sections": self.sections,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReportTemplate":
        template = cls(
            title=data["title"],
            sections=data.get("sections", []),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
        )
        template.id = data.get("id", template.id)
        template.created_at = data.get("created_at", template.created_at)
        template.updated_at = data.get("updated_at", template.updated_at)
        return template

    def save(self, filepath: str) -> bool:
        try:
            directory = os.path.dirname(os.path.abspath(filepath))
            os.makedirs(directory, exist_ok=True)
            temporary = f"{filepath}.tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2)
            os.replace(temporary, filepath)
            return True
        except (OSError, TypeError, ValueError) as error:
            logger.error("Error saving template: %s", error)
            return False

    @classmethod
    def load(cls, filepath: str) -> Optional["ReportTemplate"]:
        try:
            with open(filepath, encoding="utf-8") as handle:
                return cls.from_dict(json.load(handle))
        except (OSError, KeyError, TypeError, ValueError) as error:
            logger.error("Error loading template: %s", error)
            return None
