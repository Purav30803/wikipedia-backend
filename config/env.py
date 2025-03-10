from dotenv import load_dotenv
import os

load_dotenv()

class Env:
    DATABASE_URL = os.getenv("DATABASE_URL")
    ALLOW_IP= os.getenv("ALLOW_IP")
    IPSTACK_API_KEY = os.getenv("IPSTACK_API_KEY")