from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "analyze_git_history.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location(
    "git_codebase_audit_script",
    MODULE_PATH,
)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = MODULE
MODULE_SPEC.loader.exec_module(MODULE)


class AnalyzeGitHistoryTests(unittest.TestCase):
    def test_parse_ranked_counts_keeps_name_with_spaces(self) -> None:
        parsed_rows = MODULE.parse_ranked_counts("  12 src/app.py\n  3 docs/file name.md\n")

        self.assertEqual(parsed_rows, [(12, "src/app.py"), (3, "docs/file name.md")])

    def test_build_overlap_rows_sorts_by_risk_score(self) -> None:
        churn_rows = [(8, "src/high.py"), (4, "src/medium.py"), (2, "src/low.py")]
        bug_rows = [(3, "src/medium.py"), (2, "src/high.py"), (4, "src/low.py")]

        overlap_rows = MODULE.build_overlap_rows(churn_rows, bug_rows, limit=3)

        self.assertEqual(
            [(row.path, row.risk_score) for row in overlap_rows],
            [("src/high.py", 16), ("src/medium.py", 12), ("src/low.py", 8)],
        )

    def test_build_contributor_findings_reports_concentration_and_inactivity(self) -> None:
        contributors = [
            MODULE.ContributorRow(
                name="Alice",
                commits=9,
                share=75.0,
                last_active="2025-10-10",
                recent_commits=0,
            ),
            MODULE.ContributorRow(
                name="Bob",
                commits=3,
                share=25.0,
                last_active="2026-04-01",
                recent_commits=2,
            ),
        ]

        findings = MODULE.build_contributor_findings(
            contributors,
            recent_active_contributor_count=1,
            recent_activity_since="6 months ago",
        )

        self.assertIn("버스 팩터 위험 신호", findings[1])
        self.assertIn("유지보수 공백 가능성", findings[2])
        self.assertIn("1명 / 전체 2명", findings[3])


if __name__ == "__main__":
    unittest.main()
