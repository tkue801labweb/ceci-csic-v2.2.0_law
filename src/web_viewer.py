import os
import logging
from typing import Dict, List
from bson.objectid import ObjectId
from flask import Flask, jsonify, render_template, request  # 新增
from src.mongodb_read_data import concate_ancestor_entries_unit_number as legacy_hierarchy
from src.utils.mongodb import get_database
from src.utils.mongodb import concate_ancestor_entries_unit_number as db_hierarchy  # ✅ 新增這行

app = Flask(__name__)


logging.basicConfig(level=logging.DEBUG)


@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

def get_regulation_content(regulation_title: str) -> dict:
    """獲取法規內容（不再預先產生每條的 hierarchy_path）"""
    print(f"[DEBUG] 嘗試讀取法規：{regulation_title}")

    try:
        db = get_database()
        print("[DEBUG] 成功連接資料庫")
    except Exception as e:
        print(f"[ERROR] 無法連接資料庫: {e}")
        return {
            'meta_data': '資料庫連線失敗',
            'entries': [],
            'title': regulation_title
        }

    regulations_collection = db['regulations']
    regulation = regulations_collection.find_one({'title': regulation_title})

    if not regulation:
        print(f"[DEBUG] 找不到法規: {regulation_title}")
        return {
            'meta_data': f'⚠️ 無法找到名為「{regulation_title}」的法規。',
            'entries': [],
            'title': regulation_title
        }

    print(f"[DEBUG] 找到法規：{regulation['_id']} - {regulation.get('title')}")

    entries_collection = db['entries']
    entries = list(entries_collection.find({'regulation_id': regulation['_id']}))

    print(f"[DEBUG] 找到條文數量：{len(entries)}")


    return {
        'meta_data': regulation.get('meta_data', ''),
        'entries': entries,
        'title': regulation_title
    }


@app.route('/')
def index():
    """首頁"""
    return render_template('index.html')


@app.route('/regulation/<title>')
def show_regulation(title: str):
    """顯示特定法規內容頁面"""
    content = get_regulation_content(title)
    return render_template('regulation.html', content=content)


@app.route('/api/hierarchy/<entry_id>')
def get_hierarchy(entry_id: str):
    try:
        db = get_database()
        entry_oid = ObjectId(entry_id)
        hierarchy_path = db_hierarchy(db, entry_oid)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'hierarchy': hierarchy_path})


@app.route('/api/regulation_search/<regulation_title>')
def search_regulation_entries(regulation_title):
    """在特定法規下以關鍵字搜尋條文內容"""
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify({'entries': []})

    try:
        db = get_database()
        regulations_collection = db['regulations']
        regulation = regulations_collection.find_one({'title': regulation_title})
        if not regulation:
            return jsonify({'entries': []})
        entries_collection = db['entries']
        # 只搜尋該法規下的條文
        query = {
            'regulation_id': regulation['_id'],
            'content': {'$regex': keyword, '$options': 'i'}
        }
        entries = list(entries_collection.find(query))
        # 只回傳必要欄位
        result = [
            {
                '_id': str(entry['_id']),
                'content': entry['content']
            }
            for entry in entries
        ]
        return jsonify({'entries': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
