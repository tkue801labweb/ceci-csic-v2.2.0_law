from pathlib import Path
from src.utils.mongodb import get_database, get_regulation_id 
from bson import ObjectId


def full_text_search(search_text: str):

    db = get_database()
    collection_entries = db['entries']

    query = {'content': {'$regex': search_text}}
    results = collection_entries.find(query)

    return list(results)


def context_entries_search(entry_id: str):
    db = get_database()
    collection_name = 'entries'
    collection_entries = db[collection_name]

    # ✅ 確保 _id 是 ObjectId 類型
    if isinstance(entry_id, str):
        entry_id = ObjectId(entry_id)

    query_result = collection_entries.aggregate(
        [
            {'$match': {'_id': entry_id}},
            {
                '$graphLookup': {
                    'from': collection_name,
                    'startWith': '$parent_id',  # ✅ 改為 parent_id
                    'connectFromField': 'parent_id',
                    'connectToField': '_id',
                    'as': 'ancestors',
                    'depthField': 'ancestorLevel',
                }
            },
            {
                '$graphLookup': {
                    'from': collection_name,
                    'startWith': '$_id',
                    'connectFromField': '_id',
                    'connectToField': 'parent_id',
                    'as': 'descendants',
                    'depthField': 'descendantLevel',
                }
            },
        ]
    )

    query_result = list(query_result)
    if len(query_result) != 1:
        raise ValueError(
            f'Expected exactly one result to match the query, but found {len(query_result)}'
        )

    return query_result[0]


def concate_ancestor_entries_content(entry_id: str):
    context_entries = context_entries_search(entry_id)
    this_entry_content = context_entries['content']
    ancestor_entries = context_entries_search(entry_id)['ancestors']

    result_content = ''
    ancestor_entries.sort(key=lambda x: x['ancestorLevel'], reverse=True)
    for ancestor in ancestor_entries:
        result_content += ancestor['content'] + '\n'
    result_content += this_entry_content
    return result_content


def concate_ancestor_entries_unit_number(entry_id: str):
    context_entries = context_entries_search(entry_id)
    this_entry_unit_number = context_entries['unit_number']
    ancestor_entries = context_entries_search(entry_id)['ancestors']

    result_unit_number = ''
    ancestor_entries.sort(key=lambda x: x['ancestorLevel'], reverse=True)
    for ancestor in ancestor_entries:
        result_unit_number += ancestor['unit_number'] + ', '
    result_unit_number += this_entry_unit_number
    return result_unit_number


def deduplicate_content_list(content_list: list):
    """Deduplicates a list of content"""
    content_list.sort(key=lambda x: len(x))
    for i, content in enumerate(content_list):
        for j in range(i + 1, len(content_list)):
            if content in content_list[j]:
                content_list[j] = ''
    return [content for content in content_list if content]


def save_regulation_entries(regulation_title, save_dir):
    db = get_database()

    save_dir_path: Path = Path(save_dir) / regulation_title
    if not save_dir_path.exists():
        save_dir_path.mkdir(parents=True, exist_ok=True)

    collection = db['entries']

    regulation_id = get_regulation_id(db, regulation_title)
    query = {'regulation_id': regulation_id}
    documents = collection.find(query)

    for document in documents:
        filename = document['content'].split('\n')[0].strip()
        save_file_path = save_dir_path / filename
        with open(save_file_path, 'w', encoding='utf-8') as f:
            f.write(document['content'])

