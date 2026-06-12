"""Mem0 bridge (disabled by default in tests)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from agent import mem0_memory


class Mem0MemoryTests(unittest.TestCase):
    def test_add_skipped_when_disabled(self) -> None:
        with patch.object(mem0_memory.config, "MEM0_ENABLED", False):
            result = mem0_memory.add_memory("hello")
        self.assertFalse(result.get("ok"))
        self.assertTrue(result.get("skipped"))

    def test_search_returns_empty_when_disabled(self) -> None:
        with patch.object(mem0_memory.config, "MEM0_ENABLED", False):
            hits = mem0_memory.search_memories("preferences")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
