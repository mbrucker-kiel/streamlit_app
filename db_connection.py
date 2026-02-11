import os
from pymongo import MongoClient
import mariadb
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


def get_mariadb_connection():
    """Establish connection to MariaDB and return the connection object"""
    kwargs = {
        "host": os.getenv("MARIADB_HOST"),
        "user": os.getenv("MARIADB_USER"),
        "password": os.getenv("MARIADB_PASSWORD"),
        "database": os.getenv("MARIADB_DATABASE"),
    }

    port = os.getenv("MARIADB_PORT")
    if port:
        kwargs["port"] = int(port)

    return mariadb.connect(**kwargs)


def close_mariadb_connection(conn):
    """Close the MariaDB connection"""
    if conn:
        conn.close()
