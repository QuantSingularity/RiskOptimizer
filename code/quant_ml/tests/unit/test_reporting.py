import datetime
import json
import os

import pandas as pd
import pytest
from quant_ml.reporting import (
    ReportArchive,
    ReportGenerator,
    ReportScheduler,
    ReportTemplate,
)
from quant_ml.reporting.scheduler import add_months, ensure_within


@pytest.fixture
def template():
    t = ReportTemplate(
        "Risk Report", description="Weekly", author="Desk", version="2.0"
    )
    t.add_section("Overview", "Plain **bold** text", "text")
    t.add_section(
        "Metrics", {"data_key": "metrics", "options": {"show_index": False}}, "table"
    )
    t.add_section(
        "Series",
        {
            "data_key": "series",
            "chart_type": "line",
            "options": {"title": "S", "grid": True},
        },
        "chart",
    )
    return t


@pytest.fixture
def data():
    return {
        "metrics": pd.DataFrame({"Metric": ["VaR"], "Value": [0.03]}),
        "series": {"x": [1, 2, 3], "y": [3, 1, 2]},
    }


class TestTemplate:
    def test_section_management(self, template):
        assert len(template.sections) == 3
        section_id = template.sections[0]["id"]
        assert template.update_section(section_id, title="New", section_type="text")
        assert template.sections[0]["title"] == "New"
        assert template.remove_section(section_id)
        assert not template.remove_section("missing")
        assert not template.update_section("missing", title="x")

    def test_positioned_insert(self, template):
        template.add_section("First", "x", position=0)
        assert template.sections[0]["title"] == "First"

    def test_invalid_input(self, template):
        with pytest.raises(ValueError):
            ReportTemplate("  ")
        with pytest.raises(ValueError):
            template.add_section("x", "y", "video")
        with pytest.raises(ValueError):
            ReportTemplate("t", sections=["not an object"])
        with pytest.raises(ValueError):
            ReportTemplate("t", sections=[{"type": "bogus"}])

    def test_save_load_round_trip(self, template, tmp_path):
        path = str(tmp_path / "nested" / "t.json")
        assert template.save(path)
        loaded = ReportTemplate.load(path)
        assert loaded.to_dict() == template.to_dict()

    def test_load_failures_return_none(self, tmp_path):
        assert ReportTemplate.load(str(tmp_path / "missing.json")) is None
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        assert ReportTemplate.load(str(bad)) is None
        incomplete = tmp_path / "inc.json"
        incomplete.write_text(json.dumps({"sections": []}))
        assert ReportTemplate.load(str(incomplete)) is None

    def test_save_failure(self, template, tmp_path):
        blocked = tmp_path / "file"
        blocked.write_text("x")
        assert template.save(str(blocked / "child.json")) is False


class TestGenerator:
    def test_renders_all_section_types(self, template, data):
        html = ReportGenerator(template).render_html(data)
        assert "<h1>Risk Report</h1>" in html
        assert "<strong>bold</strong>" in html
        assert "<table" in html and "0.03" in html
        assert "data:image/png;base64," in html

    def test_untrusted_content_is_escaped(self, data):
        t = ReportTemplate(
            "<script>alert(1)</script>",
            description="<img src=x onerror=alert(2)>",
            author="A&B",
        )
        t.add_section("<b>x</b>", "<script>evil()</script> text", "text")
        t.add_section("T", {"data_key": "m"}, "table")
        html = ReportGenerator(t).render_html(
            {"m": pd.DataFrame({"<i>c</i>": ["<b>v</b>"]})}
        )
        assert "<script>" not in html
        assert "<img src=x" not in html
        assert "&lt;script&gt;alert(1)" in html
        assert "&lt;b&gt;v&lt;/b&gt;" in html
        assert "A&amp;B" in html

    def test_data_cannot_override_template_fields(self, template):
        html = ReportGenerator(template).render_html(
            {"title": "HACKED", "sections": []}
        )
        assert "HACKED" not in html and "Risk Report" in html

    def test_table_class_option_is_sanitized(self):
        t = ReportTemplate("t")
        t.add_section(
            "x", {"data_key": "m", "options": {"classes": 'a" onclick="x'}}, "table"
        )
        html = ReportGenerator(t).render_html({"m": {"a": [1]}})
        assert 'onclick="x' not in html

    @pytest.mark.parametrize("chart_type", ["line", "bar", "scatter", "pie", "heatmap"])
    def test_every_chart_type(self, chart_type):
        generator = ReportGenerator(ReportTemplate("t"))
        frame = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [1, 4, 9],
                "labels": ["a", "b", "c"],
                "values": [1, 2, 3],
            }
        )
        assert len(generator.generate_chart(chart_type, frame)) > 500

    def test_invalid_chart_input_produces_message_image(self):
        generator = ReportGenerator(ReportTemplate("t"))
        assert generator.generate_chart("line", None)
        assert generator.generate_chart("unknown", {"x": [1], "y": [1]})
        assert generator.generate_chart("pie", {"a": [1]})

    def test_missing_data_and_bad_spec(self):
        t = ReportTemplate("t")
        t.add_section("a", {"data_key": "absent"}, "table")
        t.add_section("b", "just text", "chart")
        html = ReportGenerator(t).render_html({})
        assert "No data available" in html and "specification object" in html

    def test_html_file_output(self, template, data, tmp_path):
        generator = ReportGenerator(template)
        out = str(tmp_path / "deep" / "r.html")
        assert generator.generate_html(out, data) and os.path.getsize(out) > 500
        blocked = tmp_path / "file"
        blocked.write_text("x")
        assert generator.generate_html(str(blocked / "x.html"), None) is False


class TestPdf:
    @pytest.fixture
    def pdf_text(self, template, data, tmp_path):
        from pypdf import PdfReader

        path = str(tmp_path / "out" / "r.pdf")
        assert ReportGenerator(template).generate_pdf(path, data)
        reader = PdfReader(path)
        return path, reader, "\n".join(page.extract_text() for page in reader.pages)

    def test_valid_pdf_with_content(self, pdf_text, tmp_path):
        path, reader, text = pdf_text
        assert open(path, "rb").read(5) == b"%PDF-"
        assert (
            reader.metadata.title == "Risk Report" and reader.metadata.author == "Desk"
        )
        for expected in (
            "Risk Report",
            "Overview",
            "Plain bold text",
            "VaR",
            "0.03",
            "Page 1",
        ):
            assert expected in text
        assert os.listdir(os.path.dirname(path)) == ["r.pdf"]

    def test_markup_is_never_interpreted(self, tmp_path):
        from pypdf import PdfReader

        t = ReportTemplate("<b>Title</b> & Co", description="<i>desc</i>", author="A<B")
        t.add_section(
            "<script>x</script>", "Text <script>evil()</script> with **bold**", "text"
        )
        t.add_section("T", {"data_key": "m"}, "table")
        path = str(tmp_path / "x.pdf")
        assert ReportGenerator(t).generate_pdf(
            path, {"m": pd.DataFrame({"<i>c</i>": ["<b>v</b>"]})}
        )
        text = "\n".join(p.extract_text() for p in PdfReader(path).pages)
        for literal in (
            "<b>Title</b> & Co",
            "<script>x</script>",
            "<script>evil()</script>",
            "<i>c</i>",
            "<b>v</b>",
        ):
            assert literal in text

    def test_markdown_subset_and_lists(self, tmp_path):
        from pypdf import PdfReader

        t = ReportTemplate("Md")
        t.add_section(
            "S", "# Big\n\n## Medium\n\n- one\n- two\n\nA *slanted* word", "text"
        )
        path = str(tmp_path / "m.pdf")
        assert ReportGenerator(t).generate_pdf(path)
        text = "\n".join(p.extract_text() for p in PdfReader(path).pages)
        for expected in ("Big", "Medium", "one", "two", "slanted"):
            assert expected in text

    def test_large_table_paginates_and_repeats_header(self, tmp_path):
        from pypdf import PdfReader

        t = ReportTemplate("Big")
        t.add_section(
            "Rows", {"data_key": "m", "options": {"show_index": False}}, "table"
        )
        frame = pd.DataFrame(
            {"Name": [f"row{i}" for i in range(400)], "Value": range(400)}
        )
        path = str(tmp_path / "b.pdf")
        assert ReportGenerator(t).generate_pdf(path, {"m": frame})
        reader = PdfReader(path)
        assert len(reader.pages) > 3
        assert "Name" in reader.pages[1].extract_text()

    def test_chart_and_degraded_sections(self, tmp_path):
        t = ReportTemplate("C")
        t.add_section("Chart", {"data_key": "c", "chart_type": "line"}, "chart")
        t.add_section("Bad", "not a spec", "chart")
        t.add_section("Gone", {"data_key": "absent"}, "table")
        t.add_section("Weird", {"data_key": "w"}, "table")
        path = str(tmp_path / "c.pdf")
        assert ReportGenerator(t).generate_pdf(
            path, {"c": {"x": [1, 2, 3], "y": [3, 1, 2]}, "w": 5}
        )
        assert os.path.getsize(path) > 3000

    def test_failure_cleans_up(self, template, tmp_path):
        blocked = tmp_path / "file"
        blocked.write_text("x")
        assert ReportGenerator(template).generate_pdf(str(blocked / "x.pdf")) is False


class TestScheduler:
    @pytest.fixture
    def scheduler(self, tmp_path):
        return ReportScheduler(str(tmp_path / "sched"))

    @pytest.fixture
    def paths(self, scheduler, template):
        template_path = os.path.join(scheduler.storage_dir, "t.json")
        template.save(template_path)
        return template_path, os.path.join(scheduler.storage_dir, "out.html")

    def test_provider_registry_replaces_eval(self, scheduler, paths, data):
        ReportScheduler.register_data_provider("unit", lambda: data)
        schedule_id = scheduler.add_schedule("n", *paths, "daily", data_provider="unit")
        result = scheduler.run_report(schedule_id)
        assert result["success"] and os.path.exists(paths[1])

    def test_unknown_or_malicious_provider_rejected(self, scheduler, paths):
        with pytest.raises(ValueError):
            scheduler.add_schedule(
                "n", *paths, "daily", data_provider="__import__('os').system('id')"
            )

    def test_provider_removed_after_scheduling(self, scheduler, paths):
        ReportScheduler.register_data_provider("gone", lambda: {})
        schedule_id = scheduler.add_schedule("n", *paths, "daily", data_provider="gone")
        ReportScheduler.data_providers.pop("gone")
        assert "not registered" in scheduler.run_report(schedule_id)["error"]

    def test_failing_provider(self, scheduler, paths):
        def boom():
            raise RuntimeError("down")

        ReportScheduler.register_data_provider("boom", boom)
        schedule_id = scheduler.add_schedule("n", *paths, "daily", data_provider="boom")
        assert "down" in scheduler.run_report(schedule_id)["error"]

    def test_paths_are_confined(self, scheduler, paths):
        with pytest.raises(ValueError):
            scheduler.add_schedule("n", "/etc/passwd", paths[1], "daily")
        with pytest.raises(ValueError):
            scheduler.add_schedule("n", paths[0], "/tmp/escape.html", "daily")
        relaxed = ReportScheduler(scheduler.storage_dir, allow_external_paths=True)
        assert relaxed.add_schedule("n", paths[0], "/tmp/allowed_report.html", "daily")

    @pytest.mark.parametrize("frequency", ["hourly", "", None])
    def test_invalid_frequency(self, scheduler, paths, frequency):
        with pytest.raises(ValueError):
            scheduler.add_schedule("n", *paths, frequency)

    def test_delivery_is_reported_honestly(self, scheduler, paths):
        schedule_id = scheduler.add_schedule("n", *paths, "daily", recipients=["a@b.c"])
        result = scheduler.run_report(schedule_id)
        assert result["delivered"] is False and "delivery_error" in result
        sent = []
        wired = ReportScheduler(
            scheduler.storage_dir,
            delivery_handler=lambda p, r: sent.append((p, r)) or True,
        )
        assert wired.run_report(schedule_id)["delivered"] is True and sent

    def test_failing_delivery_handler(self, scheduler, paths):
        def broken(path, recipients):
            raise OSError("smtp down")

        wired = ReportScheduler(scheduler.storage_dir, delivery_handler=broken)
        schedule_id = wired.add_schedule("n", *paths, "daily", recipients=["a@b.c"])
        assert wired.run_report(schedule_id)["delivered"] is False

    def test_due_schedules_run_and_reschedule(self, scheduler, paths):
        schedule_id = scheduler.add_schedule("n", *paths, "weekly")
        assert scheduler.run_scheduled_reports() == {}
        scheduler.schedules[schedule_id]["next_run"] = (
            datetime.datetime.now() - datetime.timedelta(days=1)
        ).isoformat()
        results = scheduler.run_scheduled_reports()
        assert results[schedule_id]["success"]
        assert scheduler.schedules[schedule_id]["last_run"] is not None
        assert (
            datetime.datetime.fromisoformat(
                scheduler.schedules[schedule_id]["next_run"]
            )
            > datetime.datetime.now()
        )

    def test_persistence_and_removal(self, scheduler, paths):
        schedule_id = scheduler.add_schedule("n", *paths, "daily")
        reloaded = ReportScheduler(scheduler.storage_dir)
        assert [s["id"] for s in reloaded.list_schedules()] == [schedule_id]
        assert reloaded.remove_schedule(schedule_id) and not reloaded.remove_schedule(
            schedule_id
        )

    def test_corrupt_schedule_file(self, tmp_path):
        directory = tmp_path / "s"
        directory.mkdir()
        (directory / "schedules.json").write_text("[1, 2")
        assert ReportScheduler(str(directory)).list_schedules() == []

    def test_missing_schedule_and_template(self, scheduler, paths):
        assert scheduler.run_report("nope")["error"] == "Schedule not found"
        schedule_id = scheduler.add_schedule("n", paths[0] + "x", paths[1], "daily")
        assert "template" in scheduler.run_report(schedule_id)["error"]

    @pytest.mark.parametrize(
        "start,expected",
        [
            ((2025, 1, 31), (2025, 2, 28)),
            ((2024, 1, 31), (2024, 2, 29)),
            ((2025, 12, 15), (2026, 1, 15)),
        ],
    )
    def test_month_arithmetic_clamps_day(self, start, expected):
        assert add_months(datetime.datetime(*start), 1).date() == datetime.date(
            *expected
        )

    def test_next_run_values(self):
        base = datetime.datetime(2025, 1, 31, 15, 30)
        assert (
            ReportScheduler.calculate_next_run("monthly", base) == "2025-02-28T00:00:00"
        )
        assert (
            ReportScheduler.calculate_next_run("weekly", base) == "2025-02-07T00:00:00"
        )
        assert (
            ReportScheduler.calculate_next_run("daily", base) == "2025-02-01T00:00:00"
        )

    def test_ensure_within(self, tmp_path):
        assert ensure_within(str(tmp_path / "a"), str(tmp_path))
        with pytest.raises(ValueError):
            ensure_within(str(tmp_path / ".." / "x"), str(tmp_path))
        (tmp_path / "link").symlink_to("/etc")
        with pytest.raises(ValueError):
            ensure_within(str(tmp_path / "link" / "passwd"), str(tmp_path))


class TestArchive:
    @pytest.fixture
    def archive(self, tmp_path):
        return ReportArchive(str(tmp_path / "archive"))

    @pytest.fixture
    def report(self, tmp_path):
        path = tmp_path / "report.html"
        path.write_text("<p>one</p>\n")
        return str(path)

    def test_archive_and_list(self, archive, report):
        first = archive.archive_report(report, "risk", {"k": 1})
        second = archive.archive_report(report, "risk")
        assert first != second
        listing = archive.list_archived_reports("risk")
        assert len(listing) == 2 and any(
            item["metadata"] == {"k": 1} for item in listing
        )
        assert archive.list_archived_reports()[0]["report_type"] == "risk"
        assert archive.list_archived_reports("empty") == []

    @pytest.mark.parametrize("report_type", ["../x", "a/b", "", ".", "x" * 80, None])
    def test_report_type_cannot_escape(self, archive, report, report_type):
        with pytest.raises(ValueError):
            archive.archive_report(report, report_type)

    def test_missing_source(self, archive, tmp_path):
        assert archive.archive_report(str(tmp_path / "none.html"), "risk") is None

    def test_reads_are_confined(self, archive, report):
        stored = archive.archive_report(report, "risk")
        assert "<p>one</p>" in archive.get_report(stored)
        assert archive.get_report("/etc/passwd") is None
        assert archive.get_report(report) is None

    def test_compare(self, archive, report, tmp_path):
        first = archive.archive_report(report, "risk")
        (tmp_path / "report.html").write_text("<p>two</p>\n")
        second = archive.archive_report(report, "risk")
        diff = archive.compare_reports(first, second)
        assert "-<p>one</p>" in diff and "+<p>two</p>" in diff
        assert archive.compare_reports(first, "/etc/passwd") is None

    def test_limit_validation(self, archive):
        with pytest.raises(ValueError):
            archive.list_archived_reports(limit=0)
