import os
import unittest
from unittest.mock import patch

from app.services import address_fill_agent as agent


class AddressFillAgentConfigTests(unittest.TestCase):
    def test_resolve_provider_specific_openai_compatible_config(self) -> None:
        env = {
            "OPENAI_AGENT_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "key",
            "DEEPSEEK_MODEL": "deepseek-chat",
        }
        with patch.dict(os.environ, env, clear=True):
            config = agent._resolve_model_config()

        self.assertEqual(config.provider, "DEEPSEEK")
        self.assertEqual(config.api_key, "key")
        self.assertEqual(config.model, "deepseek-chat")
        self.assertEqual(config.base_url, "https://api.deepseek.com")

    def test_unknown_domestic_provider_requires_base_url(self) -> None:
        env = {
            "OPENAI_AGENT_PROVIDER": "xiaomi",
            "XIAOMI_API_KEY": "key",
            "XIAOMI_MODEL": "model",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(agent._agent_enabled())

    def test_extract_json_from_noisy_model_text(self) -> None:
        parsed = agent._extract_json('说明文字\n```json\n{"row_id":"1","new_level_1":"浙江省"}\n```')

        self.assertEqual(parsed["row_id"], "1")
        self.assertEqual(parsed["new_level_1"], "浙江省")

    def test_coerce_item_preserves_existing_levels(self) -> None:
        item = agent._coerce_item(
            {"row_id": "bad", "new_level_1": "江苏省", "new_level_2": "", "evidence": []},
            "1",
            {"new_level_1": "浙江省", "new_level_2": "杭州市"},
        )

        self.assertEqual(item.row_id, "1")
        self.assertEqual(item.new_level_1, "浙江省")
        self.assertEqual(item.new_level_2, "杭州市")

    def test_build_knowledge_agent_has_no_tools(self) -> None:
        with patch.object(agent, "_build_model", return_value=None):
            built = agent._build_agent(include_tools=False, instructions_suffix="knowledge only")

        self.assertEqual(built.tools, [])
        self.assertIn("knowledge only", built.instructions)

    def test_apply_item_to_row_only_fills_empty_original_fields(self) -> None:
        item = agent.AddressFillItem(
            row_id="1",
            new_level_1="浙江省",
            new_level_2="杭州市",
        )
        row = agent._apply_item_to_row(
            {"new_level_1": "", "new_level_2": "原值"},
            item,
            ["new_level_1", "new_level_2"],
        )

        self.assertEqual(row["new_level_1"], "浙江省")
        self.assertEqual(row["new_level_2"], "原值")


if __name__ == "__main__":
    unittest.main()
