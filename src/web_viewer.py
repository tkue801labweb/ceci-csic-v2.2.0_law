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


@app.route('/multi_search')
def multi_search():
    """總體查詢頁面，列出所有法規供複選"""
    try:
        db = get_database()
        regulations_collection = db['regulations']
        all_titles = [doc['title'] for doc in regulations_collection.find({}, {'title': 1})]
    except Exception as e:
        all_titles = []
    return render_template('multi_search.html', all_titles=all_titles)


@app.route('/api/multi_regulation_search', methods=['POST'])
def multi_regulation_search():
    """多法規多關鍵字查詢 API"""
    data = request.get_json()
    titles = data.get('titles', [])
    keyword = data.get('keyword', '').strip()
    if not titles or not keyword:
        return jsonify({'results': []})
    try:
        db = get_database()
        regulations_collection = db['regulations']
        entries_collection = db['entries']
        results = []
        for title in titles:
            regulation = regulations_collection.find_one({'title': title})
            if not regulation:
                continue
            query = {
                'regulation_id': regulation['_id'],
                'content': {'$regex': keyword, '$options': 'i'}
            }
            entries = list(entries_collection.find(query))
            for entry in entries:
                results.append({
                    'regulation': title,
                    'content': entry['content']
                })
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/find_entry_id', methods=['POST'])
def find_entry_id():
    """根據 regulation title 與 content 找出 entry_id"""
    data = request.get_json()
    regulation = data.get('regulation')
    content = data.get('content')
    if not regulation or not content:
        return jsonify({'entry_id': None})
    try:
        db = get_database()
        regulations_collection = db['regulations']
        entries_collection = db['entries']
        reg = regulations_collection.find_one({'title': regulation})
        if not reg:
            return jsonify({'entry_id': None})
        entry = entries_collection.find_one({'regulation_id': reg['_id'], 'content': content})
        if not entry:
            return jsonify({'entry_id': None})
        return jsonify({'entry_id': str(entry['_id'])})
    except Exception as e:
        return jsonify({'entry_id': None, 'error': str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
