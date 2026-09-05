"""Tests for the fail-closed production readiness review gate."""

from __future__ import annotations

import unittest
from dataclasses import replace

from al_kripto.readiness import (
    REQUIRED_READINESS_CHECKS,
    ReadinessCheck,
    ReadinessEvidence,
    ReadinessStatus,
    ReadinessValidationError,
    assess_production_readiness,
    readiness_payload,
)

_AS_OF_MS = 1_500


def _passing_evidence() -> tuple[ReadinessEvidence, ...]:
    return tuple(
        ReadinessEvidence(
            check=check,
            passed=True,
            reference=f"evidence://{check.value}",
            recorded_at_ms=1_000,
            valid_until_ms=2_000,
        )
        for check in REQUIRED_READINESS_CHECKS
    )


class ReadinessAssessmentTests(unittest.TestCase):
    def test_all_evidence_only_reaches_manual_review(self) -> None:
        assessment = assess_production_readiness(_passing_evidence(), as_of_ms=_AS_OF_MS)

        self.assertEqual(assessment.status, ReadinessStatus.READY_FOR_MANUAL_REVIEW)
        self.assertEqual(assessment.assessed_at_ms, _AS_OF_MS)
        self.assertEqual(assessment.failed_checks, ())
        self.assertEqual(assessment.missing_checks, ())
        self.assertEqual(assessment.passed_checks, REQUIRED_READINESS_CHECKS)

    def test_missing_evidence_fails_closed(self) -> None:
        evidence = tuple(
            item
            for item in _passing_evidence()
            if item.check is not ReadinessCheck.KILL_SWITCH_TESTED
        )

        assessment = assess_production_readiness(evidence, as_of_ms=_AS_OF_MS)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertEqual(assessment.missing_checks, (ReadinessCheck.KILL_SWITCH_TESTED,))

    def test_failed_evidence_fails_closed(self) -> None:
        evidence = tuple(
            replace(item, passed=False) if item.check is ReadinessCheck.CI_GREEN else item
            for item in _passing_evidence()
        )

        assessment = assess_production_readiness(evidence, as_of_ms=_AS_OF_MS)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertEqual(assessment.failed_checks, (ReadinessCheck.CI_GREEN,))
        self.assertEqual(assessment.missing_checks, ())

    def test_expired_evidence_fails_closed(self) -> None:
        evidence = tuple(
            replace(item, valid_until_ms=1_400)
            if item.check is ReadinessCheck.MONITORING_HEALTHY
            else item
            for item in _passing_evidence()
        )

        assessment = assess_production_readiness(evidence, as_of_ms=_AS_OF_MS)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertIn(ReadinessCheck.MONITORING_HEALTHY, assessment.failed_checks)

    def test_future_recorded_evidence_fails_closed(self) -> None:
        evidence = tuple(
            replace(item, recorded_at_ms=1_600, valid_until_ms=2_500)
            if item.check is ReadinessCheck.CI_GREEN
            else item
            for item in _passing_evidence()
        )

        assessment = assess_production_readiness(evidence, as_of_ms=_AS_OF_MS)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertIn(ReadinessCheck.CI_GREEN, assessment.failed_checks)

    def test_each_required_check_is_fail_closed_when_missing(self) -> None:
        for omitted in REQUIRED_READINESS_CHECKS:
            with self.subTest(omitted=omitted):
                evidence = tuple(item for item in _passing_evidence() if item.check is not omitted)
                assessment = assess_production_readiness(evidence, as_of_ms=_AS_OF_MS)
                self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
                self.assertIn(omitted, assessment.missing_checks)

    def test_duplicate_evidence_is_rejected(self) -> None:
        first = _passing_evidence()[0]

        with self.assertRaises(ReadinessValidationError):
            assess_production_readiness((first, first), as_of_ms=_AS_OF_MS)

    def test_unverifiable_reference_is_rejected(self) -> None:
        with self.assertRaises(ReadinessValidationError):
            ReadinessEvidence(
                check=ReadinessCheck.CI_GREEN,
                passed=True,
                reference="x",
                recorded_at_ms=1_000,
                valid_until_ms=2_000,
            )

    def test_commit_sha_reference_is_accepted(self) -> None:
        evidence = ReadinessEvidence(
            check=ReadinessCheck.CI_GREEN,
            passed=True,
            reference="a" * 40,
            recorded_at_ms=1_000,
            valid_until_ms=2_000,
        )

        self.assertEqual(evidence.reference, "a" * 40)

    def test_invalid_evidence_time_window_is_rejected(self) -> None:
        with self.assertRaises(ReadinessValidationError):
            ReadinessEvidence(
                check=ReadinessCheck.CI_GREEN,
                passed=True,
                reference="evidence://ci",
                recorded_at_ms=2_000,
                valid_until_ms=2_000,
            )

    def test_negative_assessment_time_is_rejected(self) -> None:
        with self.assertRaises(ReadinessValidationError):
            assess_production_readiness(_passing_evidence(), as_of_ms=-1)

    def test_payload_never_enables_live_trading(self) -> None:
        assessment = assess_production_readiness(_passing_evidence(), as_of_ms=_AS_OF_MS)

        payload = readiness_payload(assessment)

        self.assertEqual(payload["status"], "ready_for_manual_review")
        self.assertEqual(payload["assessed_at_ms"], _AS_OF_MS)
        self.assertFalse(payload["live_trading_enabled"])
        self.assertEqual(payload["next_action"], "manual_security_review")
        evidence_payload = payload["evidence"]
        self.assertIsInstance(evidence_payload, list)
        assert isinstance(evidence_payload, list)
        first = evidence_payload[0]
        self.assertIsInstance(first, dict)
        assert isinstance(first, dict)
        self.assertIn("recorded_at_ms", first)
        self.assertIn("valid_until_ms", first)

    def test_not_ready_payload_keeps_live_disabled(self) -> None:
        assessment = assess_production_readiness((), as_of_ms=_AS_OF_MS)

        payload = readiness_payload(assessment)

        self.assertEqual(payload["status"], "not_ready")
        self.assertFalse(payload["live_trading_enabled"])
        self.assertEqual(
            payload["next_action"],
            "complete_missing_or_failed_evidence",
        )
        missing_checks = payload["missing_checks"]
        self.assertIsInstance(missing_checks, list)
        assert isinstance(missing_checks, list)
        self.assertEqual(
            tuple(missing_checks),
            tuple(check.value for check in REQUIRED_READINESS_CHECKS),
        )


if __name__ == "__main__":
    unittest.main()
