"""
MongoDB Connection Module
Handles MongoDB connection for module content storage
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

logger = logging.getLogger(__name__)

# MongoDB connection configuration
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'lms_content')

_mongo_client = None
_mongo_db = None


def get_mongodb_connection():
    """
    Get MongoDB database connection.
    Returns None if MongoDB is not available.
    """
    global _mongo_client, _mongo_db
    
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Verify connection
            _mongo_client.admin.command('ping')
            _mongo_db = _mongo_client[MONGO_DB_NAME]
            logger.info("Connected to MongoDB successfully")
        
        return _mongo_db
    except ConnectionFailure as e:
        logger.warning(f"MongoDB connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return None


def close_mongodb_connection():
    """
    Close MongoDB connection.
    """
    global _mongo_client, _mongo_db
    
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("MongoDB connection closed")
