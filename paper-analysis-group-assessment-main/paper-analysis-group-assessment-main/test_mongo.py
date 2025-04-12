# test_mongo.py

from pymongo import MongoClient

def main():
    # 默认MongoDB监听127.0.0.1:27017
    client = MongoClient("mongodb://localhost:27017/")
    
    # 选库: myTestDB(如果不存在则自动创建)
    db = client.myTestDB
    
    # 选集合: testColl(如果不存在则自动创建)
    col = db.testColl
    
    # 插入一条文档
    res = col.insert_one({"message": "Hello from EIDF", "value": 123})
    print("Inserted document ID:", res.inserted_id)
    
    # 查询文档
    doc = col.find_one({"message": "Hello from EIDF"})
    print("Found doc:", doc)

if __name__ == "__main__":
    main()
