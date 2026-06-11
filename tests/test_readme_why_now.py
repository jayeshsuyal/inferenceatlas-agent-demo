import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

REQUIRED_BUYER_LINES = [
    "[AI spend](examples/generated/ai_spend_budget_overrun.spend_packet.md) is now budgeted, metered, and governed",
    "[Agents need identities, permissions, containment, and audit trails]",
    "[Gateways need verdicts they can trust]",
    "[AI infrastructure spend is becoming a financing and procurement layer]",
]

REQUIRED_PRODUCT_LINKS = [
    "examples/generated/ai_spend_budget_overrun.spend_packet.md",
    "businessinsider.com/satya-nadella-microsoft-how-to-manage-ai-agents-human-employees",
    "docs.portkey.ai/docs/integrations/guardrails/bring-your-own-guardrails",
    "apollo.com/insights-news/pressreleases/2026/06/apollo-leads-35-billion",
]

NAME_DROP_PATTERNS = [
    r"Altman said",
    r"Amodei said",
    r"Anthropic announced",
    r"OpenAI announced",
    r"CEO of \w+ said",
    r"Sam Altman",
    r"Dario Amodei",
]


def extract_section(text: str, heading: str) -> str:
    marker = f"{heading}\n"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


class ReadmeWhyNowTests(unittest.TestCase):
    def test_why_now_section_holds_buyer_language(self) -> None:
        readme = README.read_text(encoding="utf-8")
        why_now = extract_section(readme, "## Why Now")

        for expected in REQUIRED_BUYER_LINES:
            self.assertIn(expected, why_now)
        for link in REQUIRED_PRODUCT_LINKS:
            self.assertIn(link, why_now)
        for pattern in NAME_DROP_PATTERNS:
            self.assertIsNone(
                re.search(pattern, why_now),
                msg=f"Name-drop pattern {pattern} in Why Now; keep buyer-language",
            )

        self.assertIsNone(re.search(r"\$[\d,]+\s+(saved|wasted)", why_now))

    def test_why_now_stays_between_timeless_why_and_users(self) -> None:
        readme = README.read_text(encoding="utf-8")

        self.assertLess(readme.index("## Why It Exists"), readme.index("## Why Now"))
        self.assertLess(readme.index("## Why Now"), readme.index("## Who Uses It"))


if __name__ == "__main__":
    unittest.main()
