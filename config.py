import os
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
REDIS_URL = os.getenv("REDIS_URL")
LINK_TTL_SECONDS = os.getenv("LINK_TTL_SECONDS")
STATS_TTL_SECONDS = os.getenv("STATS_TTL_SECONDS")
