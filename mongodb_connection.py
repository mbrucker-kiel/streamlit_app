def get_mongodb_connection():
    """Establish connection to MongoDB and return the database object"""
    client = MongoClient(MONGO_URL)
    db = client[DATABASE_NAME]
    return db, client

def close_mongodb_connection(client):
    """Close the MongoDB connection"""
    if client:
        client.close()