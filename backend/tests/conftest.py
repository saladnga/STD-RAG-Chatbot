import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-ci"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
