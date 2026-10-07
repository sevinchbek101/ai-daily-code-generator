import base64
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import daily_code_agent as agent


class AgentTests(unittest.TestCase):
    def test_daily_paths_match_required_layout(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(agent, "ROOT", Path(folder)):
            paths = agent.daily_paths(dt.date(2026, 10, 7))
            self.assertEqual(paths["java"], Path(folder) / "daily/2026-10-07/java/Main.java")
            self.assertEqual(paths["csharp"], Path(folder) / "daily/2026-10-07/csharp/Program.cs")
            self.assertEqual(len(paths), 7)

    def test_validate_codes_accepts_expected_result(self):
        codes = {key: "// a sufficiently long educational example\n" for key in agent.FILES}
        codes["java"] = "public class Main { public static void main(String[] args) {} }"
        codes["csharp"] = "class Program { static void Main(string[] args) {} }"
        agent.validate_codes(codes)

    def test_secret_detection(self):
        config = {"GITHUB_TOKEN": "github-secret-123", "GEMINI_API_KEY": "gemini-secret-456"}
        self.assertTrue(agent.contains_secret("x = 'github-secret-123'", config))
        self.assertFalse(agent.contains_secret("harmless source code", config))

    def test_remote_base64_decoding(self):
        content = "print('salom')\n"
        encoded = base64.b64encode(content.encode()).decode()
        with patch.object(agent, "github_request", return_value=(200, {"type": "file", "encoding": "base64", "content": encoded})):
            self.assertEqual(agent.remote_content({"GITHUB_TOKEN": "x"}, "o", "r", "a.py"), content)

    def test_partial_local_files_are_recovered_from_cache(self):
        codes = {key: "// a sufficiently long educational example\n" for key in agent.FILES}
        codes["java"] = "public class Main { public static void main(String[] args) {} }"
        codes["csharp"] = "class Program { static void Main(string[] args) {} }"
        date = dt.date(2026, 10, 7)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(agent, "ROOT", root), patch.object(agent, "CACHE_DIR", root / ".dailycodeagent-cache"):
                paths = agent.daily_paths(date)
                paths["php"].parent.mkdir(parents=True)
                paths["php"].write_text(codes["php"], encoding="utf-8")
                agent.atomic_write(agent.CACHE_DIR / f"{date.isoformat()}.json", __import__("json").dumps(codes))
                with patch.object(agent, "generate_codes", side_effect=AssertionError("API chaqirilmasligi kerak")):
                    agent.ensure_local_codes({}, date)
                self.assertTrue(all(path.exists() for path in paths.values()))


if __name__ == "__main__":
    unittest.main()
