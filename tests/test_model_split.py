import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_utils import load_key, update_key, is_sensitive_key
from core.ask_gpt import (
    check_is_hard_task,
    resolve_api_config,
    check_api,
    ask_gpt,
    normalize_base_url,
    check_llm_support_json
)

class TestModelSplitConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Save snapshot of config
        cls._orig_enabled = load_key("model_split.enabled")
        cls._orig_hard_model = load_key("model_split.hard_tasks.model")
        cls._orig_hard_url = load_key("model_split.hard_tasks.base_url")
        cls._orig_hard_effort = load_key("model_split.hard_tasks.reasoning_effort")
        cls._orig_easy_model = load_key("model_split.easy_tasks.model")
        cls._orig_easy_url = load_key("model_split.easy_tasks.base_url")
        cls._orig_easy_effort = load_key("model_split.easy_tasks.reasoning_effort")

    @classmethod
    def tearDownClass(cls):
        # Restore snapshot
        update_key("model_split.enabled", cls._orig_enabled)
        update_key("model_split.hard_tasks.model", cls._orig_hard_model)
        update_key("model_split.hard_tasks.base_url", cls._orig_hard_url)
        update_key("model_split.hard_tasks.reasoning_effort", cls._orig_hard_effort)
        update_key("model_split.easy_tasks.model", cls._orig_easy_model)
        update_key("model_split.easy_tasks.base_url", cls._orig_easy_url)
        update_key("model_split.easy_tasks.reasoning_effort", cls._orig_easy_effort)

    def test_normalize_base_url(self):
        # Google AI Studio URL normalizations
        self.assertEqual(
            normalize_base_url("https://generativelanguage.googleapis.com/v1beta/openai/"),
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.assertEqual(
            normalize_base_url("https://generativelanguage.googleapis.com/v1beta/openai"),
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.assertEqual(
            normalize_base_url("https://generativelanguage.googleapis.com"),
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.assertEqual(
            normalize_base_url("https://generativelanguage.googleapis.com/v1beta"),
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
        # Standard OpenAI / other providers
        self.assertEqual(
            normalize_base_url("https://api.openai.com/v1"),
            "https://api.openai.com/v1"
        )
        self.assertEqual(
            normalize_base_url("https://api.deepseek.com"),
            "https://api.deepseek.com/v1"
        )

    def test_check_llm_support_json(self):
        self.assertTrue(check_llm_support_json("gemini-3.8-flash"))
        self.assertTrue(check_llm_support_json("gemini-flash-latest"))
        self.assertTrue(check_llm_support_json("gpt-4o"))
        self.assertTrue(check_llm_support_json("deepseek-chat"))
        self.assertTrue(check_llm_support_json("deepseek-reasoner"))
        self.assertFalse(check_llm_support_json(""))
        self.assertFalse(check_llm_support_json(None))

    def test_sensitive_keys_detection(self):
        self.assertTrue(is_sensitive_key("api.key"))
        self.assertTrue(is_sensitive_key("model_split.hard_tasks.key"))
        self.assertTrue(is_sensitive_key("model_split.easy_tasks.key"))
        self.assertFalse(is_sensitive_key("model_split.enabled"))
        self.assertFalse(is_sensitive_key("model_split.hard_tasks.model"))
        self.assertFalse(is_sensitive_key("model_split.hard_tasks.base_url"))

    def test_config_model_split_structure(self):
        enabled = load_key("model_split.enabled")
        self.assertIsInstance(enabled, bool)
        
        hard_tasks = load_key("model_split.hard_tasks")
        self.assertIn("model", hard_tasks)
        self.assertIn("base_url", hard_tasks)
        self.assertIn("reasoning_effort", hard_tasks)
        
        easy_tasks = load_key("model_split.easy_tasks")
        self.assertIn("model", easy_tasks)
        self.assertIn("base_url", easy_tasks)
        self.assertIn("reasoning_effort", easy_tasks)

    def test_recursive_secret_merge(self):
        # Even when .secret has model_split.hard_tasks.key, sibling keys must still exist
        base_url = load_key("model_split.hard_tasks.base_url")
        model = load_key("model_split.hard_tasks.model")
        effort = load_key("model_split.hard_tasks.reasoning_effort")
        self.assertIsNotNone(base_url)
        self.assertIsNotNone(model)
        self.assertIsNotNone(effort)

    def test_task_difficulty_classification(self):
        self.assertTrue(check_is_hard_task("logical_chunking"))
        self.assertTrue(check_is_hard_task("asr_correction_1"))
        self.assertTrue(check_is_hard_task("translate_expressiveness"))
        self.assertTrue(check_is_hard_task("punctuation"))
        self.assertTrue(check_is_hard_task("sentence_splitbymeaning"))
        
        self.assertFalse(check_is_hard_task("translate_faithfulness"))
        self.assertFalse(check_is_hard_task("summary"))
        self.assertFalse(check_is_hard_task("subtitle_trim"))
        self.assertFalse(check_is_hard_task("tts_correct_text"))
        self.assertFalse(check_is_hard_task("default"))
        self.assertFalse(check_is_hard_task(None))

    def test_resolve_api_config_when_split_disabled(self):
        update_key("model_split.enabled", False)
        
        # Hard task
        key, url, model, effort = resolve_api_config(is_hard=True)
        self.assertEqual(key, load_key("api.key"))
        self.assertEqual(url, load_key("api.base_url"))
        self.assertEqual(model, load_key("api.model"))
        self.assertEqual(effort, load_key("reasoning.hard_tasks"))
        
        # Easy task
        key, url, model, effort = resolve_api_config(is_hard=False)
        self.assertEqual(key, load_key("api.key"))
        self.assertEqual(url, load_key("api.base_url"))
        self.assertEqual(model, load_key("api.model"))
        self.assertEqual(effort, load_key("reasoning.easy_tasks"))

    def test_resolve_api_config_when_split_enabled(self):
        update_key("model_split.enabled", True)
        update_key("model_split.hard_tasks.model", "o3-mini")
        update_key("model_split.hard_tasks.base_url", "https://api.openai.com/v1")
        update_key("model_split.hard_tasks.reasoning_effort", "high")
        
        update_key("model_split.easy_tasks.model", "gpt-4o-mini")
        update_key("model_split.easy_tasks.base_url", "https://api.openai.com/v1")
        update_key("model_split.easy_tasks.reasoning_effort", "none")
        
        # Hard task
        _, url_h, model_h, effort_h = resolve_api_config(is_hard=True)
        self.assertEqual(url_h, "https://api.openai.com/v1")
        self.assertEqual(model_h, "o3-mini")
        self.assertEqual(effort_h, "high")
        
        # Easy task
        _, url_e, model_e, effort_e = resolve_api_config(is_hard=False)
        self.assertEqual(url_e, "https://api.openai.com/v1")
        self.assertEqual(model_e, "gpt-4o-mini")
        self.assertEqual(effort_e, "none")

    def test_resolve_api_config_fallback_when_fields_empty(self):
        update_key("model_split.enabled", True)
        update_key("model_split.hard_tasks.model", "")
        update_key("model_split.hard_tasks.base_url", "")
        
        _, url, model, _ = resolve_api_config(is_hard=True)
        self.assertEqual(url, load_key("api.base_url"))
        self.assertEqual(model, load_key("api.model"))

    @patch("core.ask_gpt.OpenAI")
    def test_ask_gpt_dispatch_and_reasoning_effort(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='{"status": "ok"}'))]
        mock_completion.usage = None
        mock_client.chat.completions.create.return_value = mock_completion
        
        # 1. Enable split mode
        update_key("model_split.enabled", True)
        update_key("model_split.hard_tasks.model", "gemini-3.8-flash")
        update_key("model_split.hard_tasks.base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
        update_key("model_split.hard_tasks.reasoning_effort", "high")
        
        update_key("model_split.easy_tasks.model", "deepseek-chat")
        update_key("model_split.easy_tasks.base_url", "https://api.deepseek.com/v1")
        update_key("model_split.easy_tasks.reasoning_effort", "none")
        
        # Call hard task
        with patch("core.ask_gpt.check_ask_gpt_history", return_value=False):
            with patch("core.ask_gpt.save_log"):
                res_h = ask_gpt("chunk this text", response_json=True, log_title="logical_chunking")
                self.assertEqual(res_h, {"status": "ok"})
                call_kwargs_h = mock_client.chat.completions.create.call_args[1]
                self.assertEqual(call_kwargs_h["model"], "gemini-3.8-flash")
                self.assertEqual(call_kwargs_h["extra_body"], {"reasoning_effort": "high"})
                
                # Call easy task
                res_e = ask_gpt("summarize this", response_json=True, log_title="summary")
                self.assertEqual(res_e, {"status": "ok"})
                call_kwargs_e = mock_client.chat.completions.create.call_args[1]
                self.assertEqual(call_kwargs_e["model"], "deepseek-chat")
                self.assertEqual(call_kwargs_e["extra_body"], {"reasoning_effort": "none"})

if __name__ == "__main__":
    unittest.main()
