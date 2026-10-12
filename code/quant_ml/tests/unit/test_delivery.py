import email
import smtplib
from email import policy
from unittest.mock import MagicMock

import pytest
from quant_ml.reporting import (
    DeliveryError,
    EmailDelivery,
    ReportGenerator,
    ReportScheduler,
    ReportTemplate,
    SmtpSettings,
    validate_recipients,
)


@pytest.fixture
def report(tmp_path):
    template = ReportTemplate("Delivery Report")
    template.add_section("Body", "Hello **world**", "text")
    path = tmp_path / "report.html"
    ReportGenerator(template).generate_html(str(path))
    return str(path)


def settings(**overrides):
    values = {"host": "smtp.test", "sender": "reports@example.com", "port": 587}
    values.update(overrides)
    return SmtpSettings(**values)


class TestRecipients:
    def test_valid_and_deduplicated_case_insensitively(self):
        assert validate_recipients([" A@Example.com ", "a@example.com", "b@x.org"]) == [
            "A@Example.com",
            "b@x.org",
        ]

    @pytest.mark.parametrize(
        "bad",
        [
            "nope",
            "a@b",
            "@x.com",
            "a b@x.com",
            "a@b.c\r\nBcc: evil@x.com",
            "a@b.com\r\nBcc: x@y.com",
            "<a@b.com>",
            "",
            "a@" + "x" * 300 + ".com",
        ],
    )
    def test_invalid_addresses_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_recipients([bad])

    def test_surrounding_whitespace_is_stripped_from_the_returned_address(self):
        assert validate_recipients(["a@b.com\n", "  c@d.org\t"]) == [
            "a@b.com",
            "c@d.org",
        ]

    def test_type_and_count_limits(self):
        with pytest.raises(ValueError):
            validate_recipients("a@b.com")
        with pytest.raises(ValueError):
            validate_recipients([5])
        with pytest.raises(ValueError):
            validate_recipients([f"u{i}@example.com" for i in range(51)])


class TestSettings:
    def test_unconfigured_returns_none(self):
        assert SmtpSettings.from_environment({}) is None
        assert SmtpSettings.from_environment({"QUANT_ML_SMTP_HOST": "h"}) is None
        assert EmailDelivery.from_environment({}) is None

    def test_defaults_and_overrides(self):
        env = {"QUANT_ML_SMTP_HOST": "h", "QUANT_ML_SMTP_SENDER": "a@b.com"}
        parsed = SmtpSettings.from_environment(env)
        assert (parsed.port, parsed.use_tls, parsed.use_ssl, parsed.username) == (
            587,
            True,
            False,
            None,
        )
        env.update(
            QUANT_ML_SMTP_SSL="true",
            QUANT_ML_SMTP_USER="u",
            QUANT_ML_SMTP_PASSWORD="p",
            QUANT_ML_SMTP_TIMEOUT="5",
        )
        parsed = SmtpSettings.from_environment(env)
        assert (
            parsed.port,
            parsed.use_tls,
            parsed.use_ssl,
            parsed.username,
            parsed.timeout,
        ) == (465, False, True, "u", 5.0)

    @pytest.mark.parametrize(
        "extra",
        [
            {"QUANT_ML_SMTP_PORT": "abc"},
            {"QUANT_ML_SMTP_TIMEOUT": "x"},
            {"QUANT_ML_SMTP_SENDER": "not-an-address"},
        ],
    )
    def test_invalid_environment(self, extra):
        env = {"QUANT_ML_SMTP_HOST": "h", "QUANT_ML_SMTP_SENDER": "a@b.com"}
        env.update(extra)
        with pytest.raises(ValueError):
            SmtpSettings.from_environment(env)


class TestMessageAndTransport:
    def make_factory(self, refused=None, send_error=None):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.send_message.return_value = refused or {}
        if send_error:
            connection.send_message.side_effect = send_error
        factory = MagicMock(return_value=connection)
        return factory, connection

    def test_message_headers_and_attachment(self, report):
        message = EmailDelivery(settings()).build_message(
            report, ["a@x.com", "b@x.com"]
        )
        assert (
            message["From"] == "reports@example.com"
            and message["To"] == "a@x.com, b@x.com"
        )
        assert message["Subject"] == "Scheduled report: report.html"
        attachment = next(message.iter_attachments())
        assert (
            attachment.get_filename() == "report.html"
            and attachment.get_content_type() == "text/html"
        )
        assert b"Delivery Report" in attachment.get_payload(decode=True)

    def test_tls_login_and_send_sequence(self, report):
        factory, connection = self.make_factory()
        delivery = EmailDelivery(
            settings(username="user", password="secret"), smtp_factory=factory
        )
        assert delivery(report, ["a@x.com"]) is True
        factory.assert_called_once_with("smtp.test", 587, timeout=30.0)
        connection.starttls.assert_called_once()
        connection.login.assert_called_once_with("user", "secret")
        assert connection.send_message.call_args.kwargs["to_addrs"] == ["a@x.com"]

    def test_no_tls_or_login_when_not_configured(self, report):
        factory, connection = self.make_factory()
        EmailDelivery(settings(use_tls=False), smtp_factory=factory)(
            report, ["a@x.com"]
        )
        connection.starttls.assert_not_called()
        connection.login.assert_not_called()

    def test_refused_recipients_are_an_error(self, report):
        factory, _ = self.make_factory(refused={"a@x.com": (550, b"no")})
        with pytest.raises(DeliveryError, match="refused"):
            EmailDelivery(settings(), smtp_factory=factory)(report, ["a@x.com"])

    def test_smtp_errors_are_wrapped(self, report):
        factory, _ = self.make_factory(
            send_error=smtplib.SMTPServerDisconnected("gone")
        )
        with pytest.raises(DeliveryError, match="SMTP delivery failed"):
            EmailDelivery(settings(), smtp_factory=factory)(report, ["a@x.com"])

    def test_guards(self, report, tmp_path):
        delivery = EmailDelivery(settings(), smtp_factory=MagicMock())
        with pytest.raises(DeliveryError, match="No recipients"):
            delivery(report, [])
        with pytest.raises(DeliveryError, match="not found"):
            delivery(str(tmp_path / "missing.html"), ["a@x.com"])
        with pytest.raises(ValueError):
            delivery(report, ["bad"])
        with pytest.raises(DeliveryError, match="too large"):
            EmailDelivery(settings(), max_attachment_bytes=10)(report, ["a@x.com"])


class TestRealSmtpProtocol:
    def test_delivers_html_and_pdf_attachments(self, smtp_server, report, tmp_path):
        pdf_path = str(tmp_path / "report.pdf")
        template = ReportTemplate("PDF Delivery")
        template.add_section("Body", "text", "text")
        assert ReportGenerator(template).generate_pdf(pdf_path)
        delivery = EmailDelivery.from_environment(smtp_server.environment())
        assert delivery(report, ["a@example.com", "b@example.com"]) is True
        assert delivery(pdf_path, ["a@example.com"]) is True
        assert len(smtp_server.messages) == 2
        first = email.message_from_bytes(
            smtp_server.messages[0]["data"], policy=policy.default
        )
        assert first["Subject"] == "Scheduled report: report.html"
        assert smtp_server.messages[0]["to"] == ["a@example.com", "b@example.com"]
        assert next(first.iter_attachments()).get_content_type() == "text/html"
        second = email.message_from_bytes(
            smtp_server.messages[1]["data"], policy=policy.default
        )
        pdf = next(second.iter_attachments())
        assert pdf.get_content_type() == "application/pdf" and pdf.get_payload(
            decode=True
        ).startswith(b"%PDF")

    def test_server_refusal_surfaces_as_error(self, smtp_server, report):
        smtp_server.refused.add("bad@example.com")
        delivery = EmailDelivery.from_environment(smtp_server.environment())
        with pytest.raises(DeliveryError):
            delivery(report, ["bad@example.com"])

    def test_unreachable_server_is_a_delivery_error(self, report):
        delivery = EmailDelivery(
            settings(host="127.0.0.1", port=1, use_tls=False, timeout=2)
        )
        with pytest.raises(DeliveryError, match="SMTP delivery failed"):
            delivery(report, ["a@example.com"])


class TestSchedulerIntegration:
    @pytest.fixture
    def scheduled(self, tmp_path, no_smtp_environment):
        template = ReportTemplate("Scheduled")
        template.add_section("Body", "scheduled **text**", "text")
        directory = tmp_path / "sched"
        directory.mkdir()
        template.save(str(directory / "t.json"))
        return str(directory), str(directory / "t.json")

    def test_environment_configured_delivery_sends_real_mail(
        self, scheduled, smtp_server, monkeypatch
    ):
        directory, template_path = scheduled
        for key, value in smtp_server.environment().items():
            monkeypatch.setenv(key, value)
        scheduler = ReportScheduler(directory)
        schedule_id = scheduler.add_schedule(
            "n",
            template_path,
            f"{directory}/o.html",
            "daily",
            recipients=["ops@example.com"],
        )
        result = scheduler.run_report(schedule_id)
        assert result["delivered"] is True and "delivery_error" not in result
        assert smtp_server.messages[0]["to"] == ["ops@example.com"]

    def test_pdf_schedule_is_generated_and_attached(
        self, scheduled, smtp_server, monkeypatch
    ):
        directory, template_path = scheduled
        for key, value in smtp_server.environment().items():
            monkeypatch.setenv(key, value)
        scheduler = ReportScheduler(directory)
        schedule_id = scheduler.add_schedule(
            "n",
            template_path,
            f"{directory}/o.pdf",
            "weekly",
            recipients=["ops@example.com"],
        )
        result = scheduler.run_report(schedule_id)
        assert result["success"] and result["delivered"] is True
        message = email.message_from_bytes(
            smtp_server.messages[0]["data"], policy=policy.default
        )
        assert next(message.iter_attachments()).get_content_type() == "application/pdf"

    def test_real_failure_reason_is_reported(self, scheduled, monkeypatch):
        directory, template_path = scheduled
        monkeypatch.setenv("QUANT_ML_SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("QUANT_ML_SMTP_PORT", "1")
        monkeypatch.setenv("QUANT_ML_SMTP_SENDER", "r@example.com")
        monkeypatch.setenv("QUANT_ML_SMTP_TLS", "false")
        monkeypatch.setenv("QUANT_ML_SMTP_TIMEOUT", "2")
        scheduler = ReportScheduler(directory)
        schedule_id = scheduler.add_schedule(
            "n",
            template_path,
            f"{directory}/o.html",
            "daily",
            recipients=["ops@example.com"],
        )
        result = scheduler.run_report(schedule_id)
        assert result["success"] and result["delivered"] is False
        assert "SMTP delivery failed" in result["delivery_error"]

    def test_invalid_recipients_rejected_when_scheduling(self, scheduled):
        directory, template_path = scheduled
        scheduler = ReportScheduler(directory)
        with pytest.raises(ValueError):
            scheduler.add_schedule(
                "n", template_path, f"{directory}/o.html", "daily", recipients=["bad"]
            )

    def test_environment_delivery_can_be_disabled(
        self, scheduled, smtp_server, monkeypatch
    ):
        directory, _ = scheduled
        for key, value in smtp_server.environment().items():
            monkeypatch.setenv(key, value)
        assert (
            ReportScheduler(directory, use_environment_delivery=False).delivery_handler
            is None
        )
