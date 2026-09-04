"""Tests for the fail-closed production readiness review gate."""

from __future__ import annotations

import unittest

from al_kripto.readiness import (
    REQUIRED_READINESS_CHECKS,
    ReadinessCheck,
    ReadinessEvidence,
    ReadinessStatus,
    ReadinessValidationError,
    assess_production_readiness,
    readiness_payload,
)


def _passing_evidence() -> tuple[ReadinessEvidence, ...]:
    return tuple(
        ReadinessEvidence(
            check=check,
            passed=True,
            reference=f"evidence://{check.value}",
        )
        for check in REQUIRED_READINESS_CHECKS
    )


class ReadinessAssessmentTests(unittest.TestCase):
    def test_all_evidence_only_reaches_manual_review(self) -> None:
        assessment = assess_production_readiness(_passing_evidence())

        self.assertEqual(assessment.status, ReadinessStatus.READY_FOR_MANUAL_REVIEW)
        self.assertEqual(assessment.failed_checks, ())
        self.assertEqual(assessment.missing_checks, ())
        self.assertEqual(assessment.passed_checks, REQUIRED_READINESS_CHECKS)

    def test_missing_evidence_fails_closed(self) -> None:
        evidence = tuple(
            item
            for item in _passing_evidence()
            if item.check is not ReadinessCheck.KILL_SWITCH_TESTED
        )

        assessment = assess_production_readiness(evidence)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertEqual(assessment.missing_checks, (ReadinessCheck.KILL_SWITCH_TESTED,))

    def test_failed_evidence_fails_closed(self) -> None:
        evidence = tuple(
            ReadinessEvidence(
                check=item.check,
                passed=False if item.check is ReadinessCheck.CI_GREEN else item.passed,
                reference=item.reference,
            )
            for item in _passing_evidence()
        )

        assessment = assess_production_readiness(evidence)

        self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
        self.assertEqual(assessment.failed_checks, (ReadinessCheck.CI_GREEN,))
        self.assertEqual(assessment.missing_checks, ())

    def test_each_required_check_is_fail_closed_when_missing(self) -> None:
        for omitted in REQUIRED_READINESS_CHECKS:
            with self.subTest(omitted=omitted):
                evidence = tuple(
                    item for item in _passing_evidence() if item.check is not omitted
                )
                assessment = assess_production_readiness(evidence)
                self.assertEqual(assessment.status, ReadinessStatus.NOT_READY)
                self.assertIn(omitted, assessment.missing_checks)

    def test_duplicate_evidence_is_rejected(self) -> None:
        first = _passing_evidence()[0]

        with self.assertRaises(ReadinessValidationError):
            assess_production_readiness((first, first))

    def test_empty_reference_is_rejected(self) -> None:
        with self.assertRaises(ReadinessValidationError):
            ReadinessEvidence(
                check=ReadinessCheck.CI_GREEN,
                passed=True,
                reference="   ",
            )

    def test_payload_never_enables_live_trading(self) -> None:
        assessment = assess_production_readiness(_passing_evidence())

        payload = readiness_payload(assessment)

        self.assertEqual(payload["status"], "ready_for_manual_review")
        self.assertFalse(payload["live_trading_enabled"])
        self.assertEqual(payload["next_action"], "manual_security_review")

    def test_not_ready_payload_keeps_live_disabled(self) -> None:
        assessment = assess_production_readiness(())

        payload = readiness_payload(assessment)

        self.assertEqual(payload["status"], "not_ready")
        self.assertFalse(payload["live_trading_enabled"])
        self.assertEqual(
            payload["next_action"],
            "complete_missing_or_failed_evidence",
        )
        self.assertEqual(
            tuple(payload["missing_checks"]),
            tuple(check.value for check in REQUIRED_READINESS_CHECKS),
        )


if __name__ == "__main__":
    unittest.main()
