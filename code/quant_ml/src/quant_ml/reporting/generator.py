import base64
import html
import logging
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import jinja2
import pandas as pd
from markupsafe import Markup
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from quant_ml.reporting import pdf as pdf_module
from quant_ml.reporting.template import ReportTemplate

try:
    import markdown as markdown_module
except ImportError:
    markdown_module = None

logger = logging.getLogger(__name__)

CHART_TYPES = ("line", "bar", "scatter", "pie", "heatmap")
MAX_CHART_POINTS = 100_000
MAX_TABLE_ROWS = 5_000
CLASS_PATTERN = re.compile(r"[^A-Za-z0-9 _-]")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }
h1, h2, h3 { color: #2c3e50; }
.header { border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
.section { margin-bottom: 30px; }
.section-title { border-bottom: 1px solid #eee; padding-bottom: 5px; }
table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background-color: #f2f2f2; }
.chart { max-width: 100%; height: auto; }
.footer { border-top: 1px solid #eee; padding-top: 10px; margin-top: 30px; font-size: 0.8em; color: #777; }
</style>
</head>
<body>
<div class="header">
<h1>{{ title }}</h1>
{% if description %}<p>{{ description }}</p>{% endif %}
<p>{% if author %}Author: {{ author }} | {% endif %}Version: {{ version }} | Date: {{ date }}</p>
</div>
{% for section in sections %}
<div class="section">
{% if section.title %}<h2 class="section-title">{{ section.title }}</h2>{% endif %}
{{ section.body }}
</div>
{% endfor %}
<div class="footer">Generated on {{ generated_at }}</div>
</body>
</html>
"""


def markdown_to_html(text: str) -> Markup:
    escaped = html.escape(text, quote=False)
    if markdown_module is None:
        return Markup("<p>" + escaped.replace("\n", "<br>") + "</p>")
    return Markup(markdown_module.markdown(escaped))


def coerce_frame(data: Any) -> Optional[pd.DataFrame]:
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, dict):
        try:
            return pd.DataFrame(data)
        except ValueError:
            return None
    if isinstance(data, list):
        try:
            return pd.DataFrame(data)
        except ValueError:
            return None
    return None


class ReportGenerator:
    def __init__(self, template: ReportTemplate) -> None:
        self.template = template
        self.jinja_env = jinja2.Environment(autoescape=True)

    def build_context(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        lookup = data or {}
        sections = []
        for section in self.template.sections:
            sections.append(
                {
                    "title": section.get("title", ""),
                    "body": self.render_section(section, lookup),
                }
            )
        now = datetime.now()
        return {
            "title": self.template.title,
            "description": self.template.description,
            "author": self.template.author,
            "version": self.template.version,
            "date": now.strftime("%Y-%m-%d"),
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "sections": sections,
        }

    def render_section(self, section: Dict[str, Any], data: Dict[str, Any]) -> Markup:
        kind = section.get("type", "text")
        content = section.get("content", "")
        if kind == "text":
            return markdown_to_html(
                content if isinstance(content, str) else str(content)
            )
        if not isinstance(content, dict):
            return Markup("<p>Section content must be a specification object</p>")
        source = data.get(content.get("data_key", ""))
        if source is None:
            return Markup("<p>No data available for this section</p>")
        if kind == "chart":
            image = self.generate_chart(
                content.get("chart_type", "line"), source, content.get("options", {})
            )
            return Markup(
                f'<img class="chart" alt="chart" src="data:image/png;base64,{image}">'
            )
        if kind == "table":
            return Markup(self.generate_table(source, content.get("options", {})))
        return Markup("<p>Unsupported section type</p>")

    def render_html(self, data: Optional[Dict[str, Any]] = None) -> str:
        template = self.jinja_env.from_string(HTML_TEMPLATE)
        return template.render(**self.build_context(data))

    def generate_html(
        self, output_path: str, data: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            content = self.render_html(data)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(content)
            return True
        except Exception as error:
            logger.error("Error generating HTML report: %s", error)
            return False

    def generate_pdf(
        self, filepath: str, data: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            lookup = data or {}
            styles = pdf_module.build_styles()
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

            def render(section: Dict[str, Any], width: float) -> List[Any]:
                return self.pdf_section(section, lookup, width, styles)

            temporary = f"{filepath}.tmp"
            pdf_module.build_pdf(
                temporary,
                self.template.title,
                self.template.description,
                self.template.author,
                self.template.version,
                self.template.sections,
                render,
            )
            os.replace(temporary, filepath)
            return True
        except Exception as error:
            logger.error("Error generating PDF report: %s", error)
            return False

    def pdf_section(
        self,
        section: Dict[str, Any],
        data: Dict[str, Any],
        width: float,
        styles: Dict[str, Any],
    ) -> List[Any]:
        kind = section.get("type", "text")
        content = section.get("content", "")
        if kind == "text":
            return pdf_module.text_flowables(
                content if isinstance(content, str) else str(content), styles
            )
        if not isinstance(content, dict):
            return [
                pdf_module.paragraph_flowable(
                    "Section content must be a specification object", styles
                )
            ]
        source = data.get(content.get("data_key", ""))
        if source is None:
            return [
                pdf_module.paragraph_flowable(
                    "No data available for this section", styles
                )
            ]
        options = content.get("options", {})
        if kind == "chart":
            png = self.render_chart_png(
                content.get("chart_type", "line"), source, options
            )
            return [pdf_module.image_flowable(png, width)]
        frame = coerce_frame(source)
        if frame is None:
            return [
                pdf_module.paragraph_flowable("Invalid data format for table", styles)
            ]
        return [
            pdf_module.table_flowable(
                frame, bool(options.get("show_index", True)), width, styles
            )
        ]

    def generate_chart(
        self, chart_type: str, data: Any, options: Optional[Dict[str, Any]] = None
    ) -> str:
        return base64.b64encode(
            self.render_chart_png(chart_type, data, options)
        ).decode("ascii")

    def render_chart_png(
        self, chart_type: str, data: Any, options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        options = options or {}
        figure = Figure(figsize=(10, 6))
        axes = figure.subplots()
        frame = coerce_frame(data)
        message = None
        if chart_type not in CHART_TYPES:
            message = f"Unsupported chart type: {chart_type}"
        elif frame is None or frame.empty:
            message = f"Invalid data format for {chart_type} chart"
        elif frame.size > MAX_CHART_POINTS:
            message = "Chart data is too large"
        if message is None:
            numeric = frame.select_dtypes("number")
            if chart_type == "line":
                self.draw_xy(axes, frame, "plot")
            elif chart_type == "bar":
                self.draw_xy(axes, frame, "bar")
            elif chart_type == "scatter":
                if {"x", "y"} <= set(frame.columns):
                    axes.scatter(frame["x"], frame["y"])
                elif numeric.shape[1] >= 2:
                    axes.scatter(numeric.iloc[:, 0], numeric.iloc[:, 1])
                else:
                    message = "Invalid data format for scatter chart"
            elif chart_type == "pie":
                if {"labels", "values"} <= set(frame.columns):
                    axes.pie(
                        frame["values"],
                        labels=frame["labels"].astype(str),
                        autopct="%1.1f%%",
                    )
                elif frame.shape[1] >= 2:
                    axes.pie(
                        frame.iloc[:, 1],
                        labels=frame.iloc[:, 0].astype(str),
                        autopct="%1.1f%%",
                    )
                else:
                    message = "Invalid data format for pie chart"
            elif chart_type == "heatmap":
                if numeric.shape[1] >= 1:
                    image = axes.imshow(numeric.to_numpy(dtype=float), aspect="auto")
                    figure.colorbar(image, ax=axes)
                else:
                    message = "Invalid data format for heatmap"
        if message:
            axes.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)
            axes.set_axis_off()
        if options.get("title"):
            axes.set_title(str(options["title"]))
        if options.get("xlabel"):
            axes.set_xlabel(str(options["xlabel"]))
        if options.get("ylabel"):
            axes.set_ylabel(str(options["ylabel"]))
        if options.get("grid") and message is None and chart_type != "pie":
            axes.grid(True, alpha=0.3)
        if options.get("legend") and message is None and chart_type in ("line", "bar"):
            axes.legend()
        figure.tight_layout()
        buffer = BytesIO()
        FigureCanvasAgg(figure).print_png(buffer)
        return buffer.getvalue()

    @staticmethod
    def draw_xy(axes: Any, frame: pd.DataFrame, kind: str) -> None:
        if {"x", "y"} <= set(frame.columns):
            getattr(axes, kind)(frame["x"], frame["y"])
        elif kind == "plot":
            frame.plot(ax=axes)
        else:
            frame.plot(kind="bar", ax=axes)

    def generate_table(
        self, data: Any, options: Optional[Dict[str, Any]] = None
    ) -> str:
        options = options or {}
        frame = coerce_frame(data)
        if frame is None:
            return "<p>Invalid data format for table</p>"
        classes = CLASS_PATTERN.sub(
            "", str(options.get("classes", "table table-striped"))
        )
        return frame.head(MAX_TABLE_ROWS).to_html(
            index=bool(options.get("show_index", True)), classes=classes, escape=True
        )
