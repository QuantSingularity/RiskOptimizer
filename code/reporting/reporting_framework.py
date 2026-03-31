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
from typing import Any

import jinja2
import markdown
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("reporting_framework")
warnings.filterwarnings("ignore")


class ReportTemplate:
    """Report template for risk reports"""

    def __init__(
        self,
        title: Any,
        sections: Any = None,
        description: Any = "",
        author: Any = "",
        version: Any = "1.0",
    ) -> None:
        """
        Initialize report template

        Args:
            title: Report title
            sections: List of section dictionaries
            description: Report description
            author: Report author
            version: Report version
        """
        self.id = str(uuid.uuid4())[:8]
        self.title = title
        self.sections = sections or []
        self.description = description
        self.author = author
        self.version = version
        self.created_at = datetime.datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_section(
        self,
        title: Any,
        content: Any = "",
        section_type: Any = "text",
        position: Any = None,
    ) -> Any:
        """
        Add section to template

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
        section_id: Any,
        title: Any = None,
        content: Any = None,
        section_type: Any = None,
    ) -> Any:
        """
        Update section in template

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

    def remove_section(self, section_id: Any) -> Any:
        """
        Remove section from template

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

    def to_dict(self) -> Any:
        """
        Convert template to dictionary

        Returns:
            dict: Template as dictionary
        """
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

    def save(self, filepath: Any) -> Any:
        """
        Save template to file

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
    def load(cls: Any, filepath: Any) -> Any:
        """
        Load template from file

        Args:
            filepath: Path to load template from

        Returns:
            template: Template instance
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
    """Report generator for risk reports"""

    def __init__(self, template: Any) -> None:
        """
        Initialize report generator

        Args:
            template: Report template
        """
        self.template = template
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__))),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )

    def generate_html(self, output_path: Any, data: Any = None) -> Any:
        """
        Generate HTML report

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

    def generate_pdf(self, filepath: Any, data: Any = None) -> Any:
        """
        Generate PDF report

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

    def _create_html_template(self) -> Any:
        """
        Create HTML template

        Returns:
            template: HTML template string
        """
        template = '\n        <!DOCTYPE html>\n        <html lang="en">\n        <head>\n            <meta charset="UTF-8">\n            <meta name="viewport" content="width=device-width, initial-scale=1.0">\n            <title>{{ title }}</title>\n            <style>\n                body {\n                    font-family: Arial, sans-serif;\n                    line-height: 1.6;\n                    color: #333;\n                    max-width: 1200px;\n                    margin: 0 auto;\n                    padding: 20px;\n                }\n                h1, h2, h3 {\n                    color: #2c3e50;\n                }\n                .header {\n                    border-bottom: 1px solid #eee;\n                    padding-bottom: 10px;\n                    margin-bottom: 20px;\n                }\n                .section {\n                    margin-bottom: 30px;\n                }\n                .section-title {\n                    border-bottom: 1px solid #eee;\n                    padding-bottom: 5px;\n                }\n                table {\n                    border-collapse: collapse;\n                    width: 100%;\n                    margin-bottom: 20px;\n                }\n                th, td {\n                    border: 1px solid #ddd;\n                    padding: 8px;\n                    text-align: left;\n                }\n                th {\n                    background-color: #f2f2f2;\n                }\n                .chart {\n                    max-width: 100%;\n                    height: auto;\n                }\n                .footer {\n                    border-top: 1px solid #eee;\n                    padding-top: 10px;\n                    margin-top: 30px;\n                    font-size: 0.8em;\n                    color: #777;\n                }\n                pre {\n                    background-color: #f5f5f5;\n                    padding: 10px;\n                    border-radius: 5px;\n                    overflow-x: auto;\n                }\n                code {\n                    font-family: Consolas, Monaco, \'Andale Mono\', monospace;\n                }\n            </style>\n        </head>\n        <body>\n            <div class="header">\n                <h1>{{ title }}</h1>\n                <p>{{ description }}</p>\n                <p><strong>Date:</strong> {{ date }}</p>\n                {% if author %}\n                <p><strong>Author:</strong> {{ author }}</p>\n                {% endif %}\n            </div>\n\n            {% for section in sections %}\n            <div class="section">\n                <h2 class="section-title">{{ section.title }}</h2>\n                {% if section.type == \'text\' %}\n                    {{ section.content|safe }}\n                {% elif section.type == \'chart\' %}\n                    <img class="chart" src="data:image/png;base64,{{ section.content }}" alt="{{ section.title }}">\n                {% elif section.type == \'table\' %}\n                    {{ section.content|safe }}\n                {% elif section.type == \'code\' %}\n                    <pre><code>{{ section.content }}</code></pre>\n                {% endif %}\n            </div>\n            {% endfor %}\n\n            <div class="footer">\n                <p>Generated on {{ generated_at }} | Version {{ version }}</p>\n            </div>\n        </body>\n        </html>\n        '
        return template

    def _prepare_context(self, data: Any = None) -> Any:
        """
        Prepare context for template rendering

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
                "title": section["title"],
                "type": section["type"],
                "content": section["content"],
            }
            if section["type"] == "text":
                if "##" in section["content"] or "*" in section["content"]:
                    processed_section["content"] = markdown.markdown(section["content"])
            elif section["type"] == "chart":
                if (
                    isinstance(section["content"], dict)
                    and "chart_type" in section["content"]
                ):
                    chart_spec = section["content"]
                    chart_data = data.get(chart_spec.get("data_key", ""), None)
                    if chart_data is not None:
                        chart_image = self._generate_chart(
                            chart_type=chart_spec["chart_type"],
                            data=chart_data,
                            options=chart_spec.get("options", {}),
                        )
                        processed_section["content"] = chart_image
            elif section["type"] == "table":
                if (
                    isinstance(section["content"], dict)
                    and "data_key" in section["content"]
                ):
                    table_spec = section["content"]
                    table_data = data.get(table_spec.get("data_key", ""), None)
                    if table_data is not None:
                        table_html = self._generate_table(
                            data=table_data, options=table_spec.get("options", {})
                        )
                        processed_section["content"] = table_html
            context["sections"].append(processed_section)
        return context

    def _render_html(self, template_str: Any, context: Any) -> Any:
        """
        Render HTML from template and context

        Args:
            template_str: Template string
            context: Context dictionary

        Returns:
            html: Rendered HTML
        """
        template = jinja2.Template(template_str)
        html = template.render(**context)
        return html

    def _generate_chart(self, chart_type: Any, data: Any, options: Any = None) -> Any:
        """
        Generate chart image

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
            elif isinstance(data, dict) and "x" in data and ("y" in data):
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
            elif isinstance(data, dict) and "x" in data and ("y" in data):
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
            elif isinstance(data, dict) and "x" in data and ("y" in data):
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
            elif isinstance(data, dict) and "values" in data and ("labels" in data):
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
        if "grid" in options and options["grid"]:
            ax.grid(True)
        if "legend" in options and options["legend"]:
            ax.legend()
        buffer = BytesIO()
        plt.tight_layout()
        fig.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return image_base64

    def _generate_table(self, data: Any, options: Any = None) -> Any:
        """
        Generate HTML table

        Args:
            data: Table data (DataFrame or dict)
            options: Table options

        Returns:
            table_html: HTML table
        """
        options = options or {}
        if isinstance(data, dict):
            data = pd.DataFrame(data)
        if isinstance(data, pd.DataFrame):
            table_html = data.to_html(
                index=options.get("show_index", True),
                classes=options.get("classes", "table table-striped"),
            )
            return table_html
        else:
            return "<p>Invalid data format for table</p>"


class ReportScheduler:
    """Scheduler for automated report generation"""

    def __init__(self, storage_dir: Any = None) -> None:
        """
        Initialize report scheduler

        Args:
            storage_dir: Directory for report storage
        """
        self.storage_dir = storage_dir or os.path.join(
            os.path.expanduser("~"), ".reports"
        )
        os.makedirs(self.storage_dir, exist_ok=True)
        self.schedules = self._load_schedules()

    def _load_schedules(self) -> Any:
        """
        Load schedules from storage

        Returns:
            schedules: Dictionary of schedules
        """
        schedule_path = os.path.join(self.storage_dir, "schedules.json")
        if os.path.exists(schedule_path):
            try:
                with open(schedule_path, "r") as f:
                    return json.load(f)
            except:
                return {}
        else:
            return {}

    def _save_schedules(self) -> Any:
        """
        Save schedules to storage

        Returns:
            success: Whether save was successful
        """
        schedule_path = os.path.join(self.storage_dir, "schedules.json")
        try:
            with open(schedule_path, "w") as f:
                json.dump(self.schedules, f, indent=2)
            return True
        except:
            return False

    def add_schedule(
        self,
        name: Any,
        template_path: Any,
        output_path: Any,
        frequency: Any,
        data_provider: Any = None,
        recipients: Any = None,
    ) -> Any:
        """
        Add report schedule

        Args:
            name: Schedule name
            template_path: Path to report template
            output_path: Path for generated reports
            frequency: Schedule frequency ('daily', 'weekly', 'monthly')
            data_provider: Function to provide data for report
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

    def remove_schedule(self, schedule_id: Any) -> Any:
        """
        Remove report schedule

        Args:
            schedule_id: ID of schedule to remove

        Returns:
            success: Whether removal was successful
        """
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            return self._save_schedules()
        else:
            return False

    def list_schedules(self) -> Any:
        """
        List all schedules

        Returns:
            schedules: List of schedule summaries
        """
        return [
            {
                "id": id,
                "name": schedule["name"],
                "frequency": schedule["frequency"],
                "last_run": schedule["last_run"],
                "next_run": schedule["next_run"],
            }
            for id, schedule in self.schedules.items()
        ]

    def run_scheduled_reports(self) -> Any:
        """
        Run all due scheduled reports

        Returns:
            results: Dictionary of results
        """
        now = datetime.datetime.now()
        results = {}
        for id, schedule in self.schedules.items():
            next_run = datetime.datetime.fromisoformat(schedule["next_run"])
            if next_run <= now:
                result = self.run_report(id)
                results[id] = result
                self.schedules[id]["last_run"] = now.isoformat()
                self.schedules[id]["next_run"] = self._calculate_next_run(
                    schedule["frequency"], now
                )
        self._save_schedules()
        return results

    def run_report(self, schedule_id: Any) -> Any:
        """
        Run specific scheduled report

        Args:
            schedule_id: ID of schedule to run

        Returns:
            result: Report generation result
        """
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
                    data = eval(schedule["data_provider"])()
                except:
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

    def _calculate_next_run(self, frequency: Any, from_date: Any = None) -> Any:
        """
        Calculate next run date

        Args:
            frequency: Schedule frequency ('daily', 'weekly', 'monthly')
            from_date: Date to calculate from (default: now)

        Returns:
            next_run: Next run date as ISO string
        """
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
        next_run = datetime.datetime(
            next_run.year, next_run.month, next_run.day, 0, 0, 0
        )
        return next_run.isoformat()

    def _send_report(self, report_path: Any, recipients: Any) -> Any:
        """
        Send report to recipients

        Args:
            report_path: Path to report file
            recipients: List of email recipients

        Returns:
            success: Whether sending was successful
        """
        logger.info(f"Sending report {report_path} to {recipients}")
        return True


class ReportArchive:
    """Archive for report versioning and comparison"""

    def __init__(self, archive_dir: Any = None) -> None:
        """
        Initialize report archive

        Args:
            archive_dir: Directory for report archive
        """
        self.archive_dir = archive_dir or os.path.join(
            os.path.expanduser("~"), ".report_archive"
        )
        os.makedirs(self.archive_dir, exist_ok=True)

    def archive_report(
        self, report_path: Any, report_type: Any, metadata: Any = None
    ) -> Any:
        """
        Archive report

        Args:
            report_path: Path to report file
            report_type: Type of report
            metadata: Additional metadata

        Returns:
            archive_path: Path to archived report
        """
        report_type_dir = os.path.join(self.archive_dir, report_type)
        os.makedirs(report_type_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(report_path)
        base_name, ext = os.path.splitext(filename)
        archive_filename = f"{base_name}_{timestamp}{ext}"
        archive_path = os.path.join(report_type_dir, archive_filename)
        try:
            import shutil

            shutil.copy2(report_path, archive_path)
            if metadata:
                metadata_path = archive_path + ".meta"
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
            logger.info(f"Report archived to {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Error archiving report: {e}")
            return None

    def list_archived_reports(self, report_type: Any = None, limit: Any = 10) -> Any:
        """
        List archived reports

        Args:
            report_type: Type of report to list (None = all)
            limit: Maximum number of reports to list

        Returns:
            reports: List of archived reports
        """
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

    def _list_reports_in_dir(self, dir_path: Any, report_type: Any, limit: Any) -> Any:
        """
        List reports in directory

        Args:
            dir_path: Directory path
            report_type: Type of report
            limit: Maximum number of reports to list

        Returns:
            reports: List of reports
        """
        reports = []
        for filename in os.listdir(dir_path):
            if filename.endswith(".meta"):
                continue
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                parts = filename.split("_")
                if len(parts) >= 2:
                    try:
                        timestamp_str = parts[-2] + "_" + parts[-1].split(".")[0]
                        timestamp = datetime.datetime.strptime(
                            timestamp_str, "%Y%m%d_%H%M%S"
                        )
                    except:
                        timestamp = datetime.datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )
                else:
                    timestamp = datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                metadata = {}
                metadata_path = file_path + ".meta"
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)
                    except:
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

    def get_report(self, report_path: Any) -> Any:
        """
        Get archived report

        Args:
            report_path: Path to archived report

        Returns:
            content: Report content
        """
        try:
            with open(report_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading report: {e}")
            return None

    def compare_reports(self, report_path1: Any, report_path2: Any) -> Any:
        """
        Compare two archived reports

        Args:
            report_path1: Path to first report
            report_path2: Path to second report

        Returns:
            diff: Report difference
        """
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
    template.add_section(
        title="Returns Distribution",
        content={
            "chart_type": "histogram",
            "data_key": "returns",
            "options": {
                "title": "Returns Distribution",
                "xlabel": "Return",
                "ylabel": "Frequency",
                "grid": True,
            },
        },
        section_type="chart",
    )
    template.save("risk_report_template.json")
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 1000)
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
            "returns": returns,
            "risk_metrics": risk_metrics,
        },
    )
    logger.info("Report generated: risk_report.html")
