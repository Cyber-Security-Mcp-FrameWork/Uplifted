import os

from dotenv import load_dotenv

load_dotenv()

# Define a variable to store the current file's directory path
# Prioritize data directory for Docker/production environments
if os.getenv("UPLIFTED_DATA"):
    BASE_PATH = os.getenv("UPLIFTED_DATA")
elif os.getenv("USE_WORKDIR", "false").lower() == "true":
    BASE_PATH = os.path.dirname(os.getcwd())
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
