"""
Reporting Framework for RiskOptimizer

This module provides a flexible reporting framework:
1. Customizable report templates
2. HTML and PDF report generation
3. Interactive report components
4. Report scheduling and distribution
5. Report versioning and comparison
"""

import base64
import datetime
import json
import logging
import os
import uuid
import warnings
from io import BytesIO
from typing import Optional

import jinja2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# FIX: import markdown at module level with a graceful fallback
try:
    import markdown as _markdown_module

    def _md_to_html(text: str) -> str:
        return _markdown_module.markdown(text)

except ImportError:
    _markdown_module = None

    def _md_to_html(text: str) -> str:
        return text


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("reporting_framework")
warnings.filterwarnings("ignore")


class ReportTemplate:
    """Report template for risk reports."""

    def __init__(
        self,
        title: str,
        sections: object = None,
        description: str = "",
        author: str = "",
        version: object = "1.0",
    ) -> None:
        """
        Initialize report template.

        Args:
            title: Report title
            sections: List of section dictionaries
            description: Report description
            author: Report author
            version: Report version
        """
        self.id = str(uuid.uuid4())[:8]
        self.title = title
        # Ensure every section has an 'id' key
        normalised = []
        for s in sections or []:
            if isinstance(s, dict) and "id" not in s:
                s = dict(s, id=str(uuid.uuid4())[:8])
            normalised.append(s)
        self.sections = normalised
        self.description = description
        self.author = author
        self.version = version
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_section(
        self,
        title: str,
        content: str = "",
        section_type: str = "text",
        position: object = None,
    ) -> "ReportTemplate":
        """
        Add section to template.

        Args:
            title: Section title
            content: Section content
            section_type: Section type ('text', 'chart', 'table', 'code')
            position: Position to insert section (None = append)

        Returns:
            self: The template instance
        """
        section = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "type": section_type,
        }
        if position is None:
            self.sections.append(section)
        else:
            self.sections.insert(position, section)
        self.updated_at = datetime.datetime.now().isoformat()
        return self

    def update_section(
        self,
        section_id: str,
        title: str = None,
        content: str = None,
        section_type: str = None,
    ) -> bool:
        """
        Update section in template.

        Args:
            section_id: ID of section to update
            title: New section title (optional)
            content: New section content (optional)
            section_type: New section type (optional)

        Returns:
            success: Whether update was successful
        """
        for section in self.sections:
            if section["id"] == section_id:
                if title is not None:
                    section["title"] = title
                if content is not None:
                    section["content"] = content
                if section_type is not None:
                    section["type"] = section_type
                self.updated_at = datetime.datetime.now().isoformat()
                return True
        return False

    def remove_section(self, section_id: str) -> bool:
        """
        Remove section from template.

        Args:
            section_id: ID of section to remove

        Returns:
            success: Whether removal was successful
        """
        for i, section in enumerate(self.sections):
            if section["id"] == section_id:
                self.sections.pop(i)
                self.updated_at = datetime.datetime.now().isoformat()
                return True
        return False

    def to_dict(self) -> dict:
        """Convert template to dictionary."""
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

    def save(self, filepath: str) -> bool:
        """
        Save template to file.

        Args:
            filepath: Path to save template

        Returns:
            success: Whether save was successful
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Template saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    @classmethod
    def load(cls, filepath: str) -> Optional["ReportTemplate"]:
        """
        Load template from file.

        Args:
            filepath: Path to load template from

        Returns:
            template: Template instance, or None on error
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
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
            logger.info(f"Template loaded from {filepath}")
            return template
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None


class ReportGenerator:
    """Report generator for risk reports."""

    def __init__(self, template: ReportTemplate) -> None:
        """
        Initialize report generator.

        Args:
            template: Report template
        """
        self.template = template
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__))),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )

    # FIX: added _get_html_template as the canonical name called by generate_html
    def _get_html_template(self) -> str:
        """Return the HTML template string. Delegates to _create_html_template."""
        return self._create_html_template()

    def generate_html(
        self, output_path: str, data: "np.ndarray | pd.DataFrame | list" = None
    ) -> bool:
        """
        Generate HTML report.

        Args:
            output_path: Path to save HTML report
            data: Data for report generation

        Returns:
            success: Whether generation was successful
        """
        try:
            template_str = self._get_html_template()
            context = self._prepare_context(data)
            html = self._render_html(template_str, context)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(html)
            return True
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return False

    def generate_pdf(
        self, filepath: str, data: "np.ndarray | pd.DataFrame | list" = None
    ) -> bool:
        """
        Generate PDF report.

        Args:
            filepath: Path to save PDF report
            data: Data for report generation

        Returns:
            success: Whether generation was successful
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            html_filepath = filepath.replace(".pdf", ".html")
            if not self.generate_html(html_filepath, data):
                return False
            if not os.path.exists(html_filepath):
                logger.error(f"HTML file not found: {html_filepath}")
                return False
            try:
                from weasyprint import HTML

                HTML(filename=html_filepath).write_pdf(filepath)
                logger.info(f"PDF report saved to {filepath}")
                return True
            except ImportError:
                logger.error("WeasyPrint not available for PDF generation")
                return False
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            return False

    def _create_html_template(self) -> str:
        """Create and return the HTML template string."""
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333;
                       max-width: 1200px; margin: 0 auto; padding: 20px; }
                h1, h2, h3 { color: #2c3e50; }
                .header { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
                .section { margin-bottom: 30px; }
                .section-title { border-bottom: 1px solid #eee; padding-bottom: 5px; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .chart { max-width: 100%; height: auto; }
                .footer { border-top: 1px solid #eee; padding-top: 10px; margin-top: 30px;
                          font-size: 0.8em; color: #777; }
                pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
                code { font-family: Consolas, Monaco, 'Andale Mono', monospace; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ title }}</h1>
                <p>{{ description }}</p>
                <p><strong>Date:</strong> {{ date }}</p>
                {% if author %}<p><strong>Author:</strong> {{ author }}</p>{% endif %}
            </div>

            {% for section in sections %}
            <div class="section">
                <h2 class="section-title">{{ section.title }}</h2>
                {% if section.type == 'text' %}
                    {{ section.content|safe }}
                {% elif section.type == 'chart' %}
                    <img class="chart" src="data:image/png;base64,{{ section.content }}" alt="{{ section.title }}">
                {% elif section.type == 'table' %}
                    {{ section.content|safe }}
                {% elif section.type == 'code' %}
                    <pre><code>{{ section.content }}</code></pre>
                {% endif %}
            </div>
            {% endfor %}

            <div class="footer">
                <p>Generated on {{ generated_at }} | Version {{ version }}</p>
            </div>
        </body>
        </html>
        """
        return template

    def _prepare_context(self, data: "np.ndarray | pd.DataFrame | list" = None) -> dict:
        """
        Prepare context for template rendering.

        Args:
            data: Data for report generation

        Returns:
            context: Context dictionary
        """
        context = {
            "title": self.template.title,
            "description": self.template.description,
            "author": self.template.author,
            "version": self.template.version,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": [],
        }
        if data:
            context.update(data)
        for section in self.template.sections:
            processed_section = {
                "title": section.get("title", ""),
                "type": section.get("type", "text"),
                "content": section.get("content", ""),
            }
            if section.get("type", "text") == "text":
                content = section.get("content", "")
                if isinstance(content, str) and ("##" in content or "*" in content):
                    # FIX: use module-level helper instead of inline __import__
                    processed_section["content"] = _md_to_html(content)
            elif section.get("type", "text") == "chart":
                if isinstance(
                    section.get("content", ""), dict
                ) and "chart_type" in section.get("content", ""):
                    chart_spec = section.get("content", "")
                    chart_data = (data or {}).get(chart_spec.get("data_key", ""), None)
                    if chart_data is not None:
                        chart_image = self._generate_chart(
                            chart_type=chart_spec["chart_type"],
                            data=chart_data,
                            options=chart_spec.get("options", {}),
                        )
                        processed_section["content"] = chart_image
            elif section.get("type", "text") == "table":
                if isinstance(
                    section.get("content", ""), dict
                ) and "data_key" in section.get("content", ""):
                    table_spec = section.get("content", "")
                    table_data = (data or {}).get(table_spec.get("data_key", ""), None)
                    if table_data is not None:
                        table_html = self._generate_table(
                            data=table_data, options=table_spec.get("options", {})
                        )
                        processed_section["content"] = table_html
            context["sections"].append(processed_section)
        return context

    def _render_html(self, template_str: str, context: dict) -> str:
        """
        Render HTML from template and context.

        Args:
            template_str: Template string
            context: Context dictionary

        Returns:
            html: Rendered HTML
        """
        # FIX: docstring moved to top of method (was unreachable after try/except)
        template = jinja2.Template(template_str)
        html = template.render(**context)
        return html

    def _generate_chart(
        self,
        chart_type: str,
        data: "np.ndarray | pd.DataFrame | list",
        options: dict = None,
    ) -> str:
        """
        Generate chart image as base64 string.

        Args:
            chart_type: Type of chart ('line', 'bar', 'scatter', 'pie', 'heatmap')
            data: Chart data
            options: Chart options

        Returns:
            image_base64: Base64 encoded image
        """
        options = options or {}
        fig, ax = plt.subplots(figsize=(10, 6))
        if chart_type == "line":
            if isinstance(data, pd.DataFrame):
                data.plot(ax=ax)
            elif isinstance(data, dict) and "x" in data and "y" in data:
                ax.plot(data["x"], data["y"])
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Invalid data format for line chart",
                    ha="center",
                    va="center",
                    fontsize=12,
                )
        elif chart_type == "bar":
            if isinstance(data, pd.DataFrame):
                data.plot(kind="bar", ax=ax)
            elif isinstance(data, dict) and "x" in data and "y" in data:
                ax.bar(data["x"], data["y"])
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Invalid data format for bar chart",
                    ha="center",
                    va="center",
                    fontsize=12,
                )
        elif chart_type == "scatter":
            if isinstance(data, pd.DataFrame) and len(data.columns) >= 2:
                ax.scatter(data.iloc[:, 0], data.iloc[:, 1])
            elif isinstance(data, dict) and "x" in data and "y" in data:
                ax.scatter(data["x"], data["y"])
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Invalid data format for scatter chart",
                    ha="center",
                    va="center",
                    fontsize=12,
                )
        elif chart_type == "pie":
            if isinstance(data, pd.DataFrame) and len(data.columns) >= 2:
                ax.pie(data.iloc[:, 1], labels=data.iloc[:, 0], autopct="%1.1f%%")
            elif isinstance(data, dict) and "values" in data and "labels" in data:
                ax.pie(data["values"], labels=data["labels"], autopct="%1.1f%%")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Invalid data format for pie chart",
                    ha="center",
                    va="center",
                    fontsize=12,
                )
        elif chart_type == "heatmap":
            if isinstance(data, pd.DataFrame):
                im = ax.imshow(data)
                plt.colorbar(im, ax=ax)
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Invalid data format for heatmap",
                    ha="center",
                    va="center",
                    fontsize=12,
                )
        else:
            ax.text(
                0.5,
                0.5,
                f"Unsupported chart type: {chart_type}",
                ha="center",
                va="center",
                fontsize=12,
            )

        if "title" in options:
            ax.set_title(options["title"])
        if "xlabel" in options:
            ax.set_xlabel(options["xlabel"])
        if "ylabel" in options:
            ax.set_ylabel(options["ylabel"])
        if options.get("grid"):
            ax.grid(True)
        if options.get("legend"):
            ax.legend()

        buffer = BytesIO()
        plt.tight_layout()
        fig.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def _generate_table(
        self, data: "np.ndarray | pd.DataFrame | list", options: dict = None
    ) -> str:
        """
        Generate HTML table.

        Args:
            data: Table data (DataFrame or dict)
            options: Table options

        Returns:
            table_html: HTML table string
        """
        options = options or {}
        if isinstance(data, dict):
            data = pd.DataFrame(data)
        if isinstance(data, pd.DataFrame):
            return data.to_html(
                index=options.get("show_index", True),
                classes=options.get("classes", "table table-striped"),
            )
        return "<p>Invalid data format for table</p>"


class ReportScheduler:
    """Scheduler for automated report generation."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        """
        Initialize report scheduler.

        Args:
            storage_dir: Directory for report storage
        """
        self.storage_dir = storage_dir or os.path.join(
            os.path.expanduser("~"), ".reports"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        self.schedules = self._load_schedules()

    def _load_schedules(self) -> dict:
        """Load schedules from storage."""
        schedule_path = os.path.join(self.storage_dir, "schedules.json")
        if os.path.exists(schedule_path):
            try:
                with open(schedule_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_schedules(self) -> bool:
        """Save schedules to storage."""
        schedule_path = os.path.join(self.storage_dir, "schedules.json")
        try:
            with open(schedule_path, "w") as f:
                json.dump(self.schedules, f, indent=2)
            return True
        except Exception:
            return False

    def add_schedule(
        self,
        name: str,
        template_path: str,
        output_path: str,
        frequency: "np.ndarray | pd.DataFrame | list",
        data_provider: object = None,
        recipients: object = None,
    ) -> bool:
        """
        Add report schedule.

        Args:
            name: Schedule name
            template_path: Path to report template
            output_path: Path for generated reports
            frequency: Schedule frequency ('daily', 'weekly', 'monthly')
            data_provider: Callable name (string) to provide data for report
            recipients: List of email recipients

        Returns:
            success: Whether addition was successful
        """
        schedule_id = str(uuid.uuid4())[:8]
        self.schedules[schedule_id] = {
            "name": name,
            "template_path": template_path,
            "output_path": output_path,
            "frequency": frequency,
            "data_provider": data_provider,
            "recipients": recipients or [],
            "last_run": None,
            "next_run": self._calculate_next_run(frequency),
            "created_at": datetime.datetime.now().isoformat(),
        }
        return self._save_schedules()

    def remove_schedule(self, schedule_id: object) -> bool:
        """Remove report schedule by ID."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return self._save_schedules()
        return False

    def list_schedules(self) -> list:
        """List all schedules."""
        return [
            {
                "id": sid,
                "name": schedule["name"],
                "frequency": schedule["frequency"],
                "last_run": schedule["last_run"],
                "next_run": schedule["next_run"],
            }
            for sid, schedule in self.schedules.items()
        ]

    def run_scheduled_reports(self) -> dict:
        """Run all due scheduled reports."""
        now = datetime.datetime.now()
        results = {}
        for sid, schedule in self.schedules.items():
            next_run = datetime.datetime.fromisoformat(schedule["next_run"])
            if next_run <= now:
                result = self.run_report(sid)
                results[sid] = result
                self.schedules[sid]["last_run"] = now.isoformat()
                self.schedules[sid]["next_run"] = self._calculate_next_run(
                    schedule["frequency"], now
                )
        self._save_schedules()
        return results

    def run_report(self, schedule_id: object) -> dict:
        """Run specific scheduled report."""
        if schedule_id not in self.schedules:
            return {"success": False, "error": "Schedule not found"}
        schedule = self.schedules[schedule_id]
        try:
            template = ReportTemplate.load(schedule["template_path"])
            if template is None:
                return {"success": False, "error": "Failed to load template"}
            generator = ReportGenerator(template)
            data = None
            if schedule["data_provider"]:
                try:
                    data = eval(schedule["data_provider"])()  # noqa: S307
                except Exception:
                    return {
                        "success": False,
                        "error": "Failed to get data from provider",
                    }
            output_path = schedule["output_path"]
            if output_path.endswith(".pdf"):
                success = generator.generate_pdf(output_path, data)
            else:
                success = generator.generate_html(output_path, data)
            if success and schedule["recipients"]:
                self._send_report(output_path, schedule["recipients"])
            return {"success": success, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _calculate_next_run(
        self, frequency: "np.ndarray | pd.DataFrame | list", from_date: object = None
    ) -> str:
        """Calculate next run date as ISO string."""
        if from_date is None:
            from_date = datetime.datetime.now()
        if frequency == "daily":
            next_run = from_date + datetime.timedelta(days=1)
        elif frequency == "weekly":
            next_run = from_date + datetime.timedelta(days=7)
        elif frequency == "monthly":
            if from_date.month == 12:
                next_run = datetime.datetime(from_date.year + 1, 1, from_date.day)
            else:
                next_run = datetime.datetime(
                    from_date.year, from_date.month + 1, from_date.day
                )
        else:
            next_run = from_date + datetime.timedelta(days=1)
        return datetime.datetime(
            next_run.year, next_run.month, next_run.day, 0, 0, 0
        ).isoformat()

    def _send_report(self, report_path: object, recipients: object) -> bool:
        """Send report to recipients (stub)."""
        logger.info(f"Sending report {report_path} to {recipients}")
        return True


class ReportArchive:
    """Archive for report versioning and comparison."""

    def __init__(self, archive_dir: object = None) -> None:
        """
        Initialize report archive.

        Args:
            archive_dir: Directory for report archive
        """
        self.archive_dir = archive_dir or os.path.join(
            os.path.expanduser("~"), ".report_archive"
        )
        os.makedirs(self.archive_dir, exist_ok=True)

    def archive_report(
        self,
        report_path: object,
        report_type: object,
        metadata: "np.ndarray | pd.DataFrame | list" = None,
    ) -> Optional[str]:
        """
        Archive report.

        Args:
            report_path: Path to report file
            report_type: Type of report
            metadata: Additional metadata

        Returns:
            archive_path: Path to archived report, or None on failure
        """
        report_type_dir = os.path.join(self.archive_dir, report_type)
        os.makedirs(report_type_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(report_path)
        base_name, ext = os.path.splitext(filename)
        archive_path = os.path.join(report_type_dir, f"{base_name}_{timestamp}{ext}")
        try:
            import shutil

            shutil.copy2(report_path, archive_path)
            if metadata:
                with open(archive_path + ".meta", "w") as f:
                    json.dump(metadata, f, indent=2)
            logger.info(f"Report archived to {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Error archiving report: {e}")
            return None

    def list_archived_reports(
        self, report_type: object = None, limit: int = 10
    ) -> list:
        """List archived reports."""
        reports = []
        if report_type:
            report_type_dir = os.path.join(self.archive_dir, report_type)
            if os.path.exists(report_type_dir):
                reports.extend(
                    self._list_reports_in_dir(report_type_dir, report_type, limit)
                )
        else:
            for dir_name in os.listdir(self.archive_dir):
                dir_path = os.path.join(self.archive_dir, dir_name)
                if os.path.isdir(dir_path):
                    reports.extend(self._list_reports_in_dir(dir_path, dir_name, limit))
        reports.sort(key=lambda r: r["timestamp"], reverse=True)
        return reports[:limit]

    def _list_reports_in_dir(
        self, dir_path: object, report_type: object, limit: object
    ) -> list:
        """List reports in a directory."""
        reports = []
        for filename in os.listdir(dir_path):
            if filename.endswith(".meta"):
                continue
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                parts = filename.split("_")
                try:
                    if len(parts) >= 2:
                        timestamp_str = parts[-2] + "_" + parts[-1].split(".")[0]
                        timestamp = datetime.datetime.strptime(
                            timestamp_str, "%Y%m%d_%H%M%S"
                        )
                    else:
                        raise ValueError("not enough parts")
                except Exception:
                    timestamp = datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                metadata = {}
                meta_path = file_path + ".meta"
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r") as f:
                            metadata = json.load(f)
                    except Exception:
                        pass
                reports.append(
                    {
                        "path": file_path,
                        "filename": filename,
                        "report_type": report_type,
                        "timestamp": timestamp,
                        "metadata": metadata,
                    }
                )
        return reports

    def get_report(self, report_path: str) -> Optional[str]:
        """Get archived report content."""
        try:
            with open(report_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading report: {e}")
            return None

    def compare_reports(self, report_path1: str, report_path2: str) -> Optional[str]:
        """Compare two archived reports and return a unified diff."""
        try:
            with open(report_path1, "r") as f:
                content1 = f.read()
            with open(report_path2, "r") as f:
                content2 = f.read()
            import difflib

            diff = difflib.unified_diff(
                content1.splitlines(),
                content2.splitlines(),
                fromfile=os.path.basename(report_path1),
                tofile=os.path.basename(report_path2),
                lineterm="",
            )
            return "\n".join(diff)
        except Exception as e:
            logger.error(f"Error comparing reports: {e}")
            return None


if __name__ == "__main__":
    template = ReportTemplate(
        title="Risk Analysis Report",
        description="Analysis of portfolio risk metrics",
        author="RiskOptimizer",
    )
    template.add_section(
        title="Portfolio Overview",
        content="This report provides an analysis of portfolio risk metrics.",
        section_type="text",
    )
    template.add_section(
        title="Risk Metrics",
        content={"data_key": "risk_metrics", "options": {"show_index": False}},
        section_type="table",
    )
    template.save("risk_report_template.json")

    np.random.seed(42)
    risk_metrics = pd.DataFrame(
        {
            "Metric": [
                "Volatility",
                "VaR (95%)",
                "ES (95%)",
                "Sharpe Ratio",
                "Max Drawdown",
            ],
            "Value": [0.02, 0.033, 0.041, 0.8, 0.15],
        }
    )
    generator = ReportGenerator(template)
    generator.generate_html(
        "risk_report.html",
        data={
            "portfolio_name": "Sample Portfolio",
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "risk_metrics": risk_metrics,
        },
    )
    logger.info("Report generated: risk_report.html")
