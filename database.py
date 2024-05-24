from pymongo import MongoClient
import os

MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['chatbot']
learning_paths_collection = db["learningPaths"]

def get_learning_paths_collection():
    return learning_paths_collection