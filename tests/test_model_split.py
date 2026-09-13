import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_utils import load_key, update_key, is_sensitive_key
from core.ask_gpt import check_is_hard_task, resolve_api_config, check_api

class TestModelSplitConfig(unittest.TestCase):
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
        
        # Reset enabled to False
        update_key("model_split.enabled", False)

    def test_resolve_api_config_fallback_when_fields_empty(self):
        update_key("model_split.enabled", True)
        update_key("model_split.hard_tasks.model", "")
        update_key("model_split.hard_tasks.base_url", "")
        
        key, url, model, _ = resolve_api_config(is_hard=True)
        self.assertEqual(key, load_key("api.key"))
        self.assertEqual(url, load_key("api.base_url"))
        self.assertEqual(model, load_key("api.model"))
        
        update_key("model_split.enabled", False)

if __name__ == "__main__":
    unittest.main()
