from pymongo import MongoClient
from bson import ObjectId
import json
import traceback

# Use your MongoDB connection string
MONGO_URI = "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['job_portal']

def get_field_type(value):
    if isinstance(value, ObjectId):
        return "ObjectId"
    elif isinstance(value, dict):
        return "Object"
    elif isinstance(value, list):
        return "Array"
    else:
        return type(value).__name__

def get_collection_structure(collection):
    if isinstance(collection, list):
        sample_docs = collection
    else:
        pipeline = [
            {"$sample": {"size": 100}},
            {"$project": {"_id": 0}},
        ]
        sample_docs = list(collection.aggregate(pipeline))
    
    if not sample_docs:
        return {}
    
    structure = {}
    for doc in sample_docs:
        for field, value in doc.items():
            if field not in structure:
                structure[field] = set()
            structure[field].add(get_field_type(value))
            
            if isinstance(value, dict):
                nested_structure = get_collection_structure([value])
                for nested_field, nested_type in nested_structure.items():
                    full_field = f"{field}.{nested_field}"
                    if full_field not in structure:
                        structure[full_field] = set()
                    structure[full_field].update(nested_type)
            elif isinstance(value, list) and value:
                array_types = set()
                for item in value:
                    array_types.add(get_field_type(item))
                    if isinstance(item, dict):
                        nested_structure = get_collection_structure([item])
                        for nested_field, nested_type in nested_structure.items():
                            full_field = f"{field}[].{nested_field}"
                            if full_field not in structure:
                                structure[full_field] = set()
                            structure[full_field].update(nested_type)
                structure[field] = [array_types]
    
    return {k: list(v) if isinstance(v, set) else v for k, v in structure.items()}

def print_structure(structure, indent=0):
    for key, value in structure.items():
        print("  " * indent + f"{key}: {value}")

print("Database structure:")
for collection_name in db.list_collection_names():
    print(f"\nCollection: {collection_name}")
    try:
        if collection_name == 'tbl_jobs':
            # Special handling for tbl_jobs
            sample_doc = db[collection_name].find_one()
            if sample_doc:
                structure = {k: [get_field_type(v)] for k, v in sample_doc.items()}
                print_structure(structure)
            else:
                print("No documents found in tbl_jobs")
        else:
            structure = get_collection_structure(db[collection_name])
            print_structure(structure)
    except Exception as e:
        print(f"Error processing collection {collection_name}:")
        print(traceback.format_exc())

client.close()