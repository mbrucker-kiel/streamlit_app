import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_mongodb_connection():
    """Establish connection to MongoDB and return the database object"""
    client = MongoClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DATABASE_NAME")]
    return db, client

def close_mongodb_connection(client):
    """Close the MongoDB connection"""
    if client:
        client.close()