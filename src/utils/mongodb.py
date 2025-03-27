import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

def get_database():
    load_dotenv()
    
    # 從環境變數獲取連線資訊
    username = os.getenv('MONGOUSER')
    password = os.getenv('MONGOPASSWORD')
    host = os.getenv('MONGOHOST')
    port = os.getenv('MONGOPORT')
    
    # 建立連線字串
    if username and password:
        CONNECTION_STRING = f'mongodb://{username}:{password}@{host}:{port}'
    else:
        CONNECTION_STRING = f'mongodb://{host}:{port}'
    
    try:
        client = MongoClient(CONNECTION_STRING)
        # 測試連線
        client.admin.command('ping')
        return client['ceci-csic']
    except ConnectionFailure as e:
        raise Exception(f"無法連接到 MongoDB: {str(e)}")

def get_regulation_id(db, regulation_title):
    collection = db['regulations']

    query = {'title': regulation_title}
    document = collection.find_one(query)

    if document:
        return document['_id']
    else:
        return None

def concate_ancestor_entries_unit_number(db, entry_id):
    """
    回傳該條目從根到目前的所有階層單位編號，格式為 '1,2,3'
    """
    collection = db['entries']
    unit_numbers = []

    current_entry = collection.find_one({'_id': entry_id})

    while current_entry:
        if 'unit_number' in current_entry:
            unit_numbers.insert(0, str(current_entry['unit_number']))
        parent_id = current_entry.get('parent_id')
        if not parent_id:
            break
        current_entry = collection.find_one({'_id': parent_id})

    return ','.join(unit_numbers)


def insert_single_entry(db, entry_data, regulation_id):
    """
    插入單條條目資料到資料庫
    
    Args:
        db: MongoDB 數據庫連接
        entry_data: 條目資料
        regulation_id: 法規 ID
        
    Returns:
        ObjectId: 插入的文檔 ID
    """
    collection = db['entries']
    
    # 確保基本欄位存在
    document = {
        'regulation_id': regulation_id,
        'unit_number': entry_data.get('unit_number'),
        'content': entry_data.get('content', ''),
        'type': entry_data.get('type', 'default'),
        'level': entry_data.get('level', 1)
    }
    
    # 如果有父層級ID，加入對應關係
    if 'parent_id' in entry_data:
        document['parent_id'] = entry_data['parent_id']
    
    # 插入文檔並返回 ID
    result = collection.insert_one(document)
    return result.inserted_id
