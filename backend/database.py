import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "stockflow")

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _client[MONGODB_DB_NAME]
    return _db


def init_database():
    db = get_db()
    # Verify connection on startup
    db.command("ping")
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.products.create_index(
        [("organization_id", ASCENDING), ("sku", ASCENDING)],
        unique=True,
    )