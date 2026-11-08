import unittest
from battle_narrative import generate_narrative

class NarrativeTests(unittest.TestCase):
    def test_generate(self):
        result = generate_narrative("test-skill", "测试场景", ["evidence-1"])
        self.assertEqual(result["skill"], "test-skill")
        self.assertTrue(result["install_command"].startswith("npx"))

if __name__ == "__main__":
    unittest.main()
