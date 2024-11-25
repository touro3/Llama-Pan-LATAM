from dotenv import load_dotenv
import os

load_dotenv()

SAMBA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
