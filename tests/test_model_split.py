import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_utils import load_key, update_key, is_sensitive_key

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

if __name__ == "__main__":
    unittest.main()
