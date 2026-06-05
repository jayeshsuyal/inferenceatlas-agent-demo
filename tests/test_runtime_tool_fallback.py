import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent import runtime


class _RepeatingToolMessage:
    content = None

    def __init__(self, call_id: str) -> None:
        self.tool_calls = [
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(name="get_catalog_summary", arguments="{}"),
            )
        ]

    def model_dump(self, exclude_unset: bool = True) -> dict:
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": self.tool_calls[0].id,
                    "type": "function",
                    "function": {
                        "name": "get_catalog_summary",
                        "arguments": "{}",
                    },
                }
            ],
        }


class _RepeatingToolClient:
    def __init__(self) -> None:
        self.calls = 0
        self.requests: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls += 1
        self.requests.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=_RepeatingToolMessage(f"call-{self.calls}"))]
        )


class RuntimeToolFallbackTests(unittest.TestCase):
    def test_builtin_tool_loop_falls_back_to_tool_results(self) -> None:
        client = _RepeatingToolClient()
        catalog_result = "InferenceAtlas Catalog: 175 entries across 16 providers."

        with patch.object(runtime, "_llm_client", return_value=client), patch.object(
            runtime, "AGENT_MAX_STEPS", 2
        ), patch.dict(
            runtime.TOOL_DISPATCH,
            {"get_catalog_summary": lambda: catalog_result},
            clear=True,
        ):
            answer = runtime._run_builtin(
                [{"role": "user", "content": "Use get_catalog_summary"}]
            )

        self.assertEqual(client.calls, 2)
        self.assertTrue(
            all(request["parallel_tool_calls"] is False for request in client.requests)
        )
        self.assertIn("Live tools returned verified output", answer)
        self.assertIn("## get_catalog_summary", answer)
        self.assertIn(catalog_result, answer)
        self.assertNotIn("[agent] max steps reached", answer)

    def test_tool_result_summary_deduplicates_repeated_results(self) -> None:
        answer = runtime._summarize_tool_results(
            [
                ("get_catalog_summary", "InferenceAtlas Catalog: 175 entries"),
                ("get_catalog_summary", "InferenceAtlas Catalog: 175 entries"),
            ]
        )

        self.assertEqual(answer.count("## get_catalog_summary"), 1)


if __name__ == "__main__":
    unittest.main()
