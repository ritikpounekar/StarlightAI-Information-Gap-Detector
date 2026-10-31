import unittest

from analysis import analyze_research


class ResearchAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {
                "name": "Portal notice",
                "type": "text",
                "text": (
                    "The 2026 scholarship is open to undergraduate applicants with household income below "
                    "INR 500,000. Applications close November 15, 2026. Applicants must upload a government "
                    "income certificate only and academic transcripts. The award provides INR 80,000 per year. "
                    "Apply through the official scholarship portal."
                ),
            },
            {
                "name": "Guideline PDF",
                "type": "pdf",
                "text": (
                    "For the 2026 scholarship, applicants must have GPA at least 3.2 and household income below "
                    "INR 500,000. Last date to apply is December 10, 2026. Applicants must submit income tax "
                    "returns only and academic transcripts. The annual scholarship amount is INR 80,000. "
                    "Applications are submitted through the scholarship portal."
                ),
            },
        ]

    def test_detects_missing_renewal_and_conflicting_deadline_and_income_proof(self):
        result = analyze_research("What should I verify before applying for this scholarship?", self.sources)
        gap_ids = {gap["id"] for gap in result["gaps"]}
        self.assertIn("gap-renewal", gap_ids)
        topics = {conflict["topic"] for conflict in result["conflicts"]}
        self.assertIn("Current application deadline", topics)
        self.assertIn("Accepted income proof", topics)

    def test_evidence_has_direct_source_citations_and_inferred_prompt_is_separate(self):
        result = analyze_research("Scholarship requirements", self.sources)
        source_claims = [item for item in result["evidence_matrix"] if not item["is_inferred"]]
        inferred = [item for item in result["evidence_matrix"] if item["is_inferred"]]
        self.assertTrue(source_claims)
        self.assertTrue(all("[Source: " in item["claim"] for item in source_claims))
        self.assertTrue(all("not a source claim" in item["confidence"].lower() for item in inferred))

    def test_coverage_is_not_mislabeled_as_truth(self):
        result = analyze_research("Scholarship details", self.sources)
        self.assertEqual(result["coverage_label"], "Source coverage, not truth score")
        self.assertEqual(result["overall_completeness_score"], 86)


if __name__ == "__main__":
    unittest.main()
