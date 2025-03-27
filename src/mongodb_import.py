import re
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from pymongo import UpdateOne
from pymongo import InsertOne
from utils.mongodb import (
    concate_ancestor_entries_unit_number,
    get_database,
    get_regulation_id,
    insert_single_entry,
)

hierarchy_pattern_map = {
    'type_1': [
        [r'^第\s*(?:[零一二三四五六七八九十]+\s*)章',
        r'^第\s*(?:[零一二三四五六七八九十]+\s*)章之[零一二三四五六七八九十]+',
        r'^第\s*(?:[零一二三四五六七八九十]+\s*)編'
        ],
        [r'^第\s*(?:[零一二三四五六七八九十]+\s*)節'],
        [r'^第\s\d+\s條', r'^第\s\d+-\d+\s條'],
        [r'^\d+\s'],
        [r'^\s*(?:[一二三四五六七八九十]+\s*)、'],
        [r'^[（(]\s*(?:[一二三四五六七八九十]+\s*)[）)]'],
    ],
    'type_2': [
        [r'^\s*(?:[一二三四五六七八九十]+\s*)、'],
        [r'^[（(]\s*(?:[一二三四五六七八九十]+\s*)[）)]'],
        [r'^[（(]\d+[）)]'],
        [r'^\d+\.'],
    ],
    'type_3': [
        [r'^\s*[壹貳參肆伍陸柒捌玖拾]+\s*、'],
        [r'^\s*(?:[一二三四五六七八九十]+\s*)、'],
        [r'^[（(]\s*(?:[一二三四五六七八九十]+\s*)[）)]'],
        [r'^\d+\s'],
        [r'^\d+\.'],
        [r'^[（(]\d+[）)]'],
    ],
    'type_4': [
        [r'^第\s*(?:[零一二三四五六七八九十百千]+\s*)+章'],
        [r'^第\s*(?:[零一二三四五六七八九十百千]+(?:\s*[零一二三四五六七八九十百千]+)*)\s*節'],
        [r'^第\s*(?:[零一二三四五六七八九十百千]+\s*)+條'],
        [r'^[一二三四五六七八九十]+、'],
        [r'^[（(]\s*(?:[一二三四五六七八九十]+\s*)[）)]'],
        [r'^\d+、'],
    ],
    'type_5': [
        [r'^\s*(?:[一二三四五六七八九十]+\s*)、'],
        [r'^[（(]\s*(?:[一二三四五六七八九十]+\s*)[）)]'],
        [r'^\d+\.'],
        [r'^[（(]\d+[）)]'],
        [r'^[iI]{1,4}\.'],
    ],
}

# 讀取法規名稱與階層類型的對應表
hierarchy_type_df = pd.read_excel('各法規階層.xlsx')
hierarchy_type_dict = dict(zip(hierarchy_type_df['檔案名稱'].str.replace('.txt', '', regex=False), hierarchy_type_df['階層類型']))

def get_hierarchy_unit_number(text: str, file_name: str) -> str:
    hierarchy_type = hierarchy_type_dict.get(file_name)
    if not hierarchy_type or hierarchy_type not in hierarchy_pattern_map:
        print(f"Warning: No hierarchy type found for file {file_name}")
        return None

    for pattern_group in hierarchy_pattern_map[hierarchy_type]:
        for pattern in pattern_group:
            match = re.match(pattern, text)
            if match:
                print(f"Match found: {match.group()} for pattern {pattern} in file {file_name}")
                return match.group()
    print(f"No match found for text: {text} in file {file_name}")
    return None


def import_regulation(db, regulation_file_path: Path):
    collection = db['regulations']
    with open(regulation_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        lines = content.split('\n')
        index = -1
        for j, line in enumerate(lines):
            if '修正日期：' in line:
                index = j + 1
                break

        pre_chapter_content = '\n'.join(lines[:index]) if index != -1 else content

        document = {
            'title': regulation_file_path.stem,
            'meta_data': pre_chapter_content,
            'full_text': content,
        }
        collection.insert_one(document)
        print(f'Regulations: inserted {regulation_file_path.stem} successfully')

# import_entry 函式與 hierarchy path 建構

def import_entry(db, markdown_dir_path: Path, regulation_txt_path: Path):
    collection = db['entries']
    file_name = regulation_txt_path.stem
    reference_id = get_regulation_id(db, file_name)

    markdown_file_path = markdown_dir_path / f'{file_name}.md'
    with open(markdown_file_path, 'r', encoding='utf-8') as file:
        regulation = file.read()
        pattern = r'(#+.*?)(?=\n#+|\Z)'
        sections = re.findall(pattern, regulation, re.DOTALL)

        parent_stack = []  # ✅ 改為堆疊型結構

        for section in sections:
            lines = section.splitlines()
            current_data = ''
            current_level = 0

            for line in lines:
                if line.startswith('#'):
                    current_level = line.count('#')
                    current_data = line
                else:
                    current_data += '\n' + line

            current_data = current_data.replace('#', '').strip()
            unit_number = get_hierarchy_unit_number(current_data, file_name)

            # ✅ 移除比自己層級大的 parent（因為不再是上層）
            while parent_stack and parent_stack[-1]['level'] >= current_level:
                parent_stack.pop()

            # ✅ 組 hierarchy_path.levels
            parent_levels = parent_stack[-1]['levels'] if parent_stack else []
            levels = parent_levels.copy()
            if unit_number:
                levels.append(unit_number.strip())

            entry_data = {
                'content': current_data,
                'unit_number': unit_number,
                'level': current_level,
                'type': 'entry',
                'regulation_id': reference_id,
                'hierarchy_path': {
                    'levels': levels
                }
            }

            if parent_stack:
                entry_data['parent_id'] = parent_stack[-1]['id']

            # ✅ 插入並立即取得 ID，再放入堆疊
            entry_id = collection.insert_one(entry_data).inserted_id
            parent_stack.append({'id': entry_id, 'level': current_level, 'levels': levels})

        print(f'Entries: inserted {file_name} successfully')



if __name__ == '__main__':
    db = get_database()
    print('Database connected successfully')

    regulations_folder_path = Path('data/regulations')
    formatted_regulations_dir_path = Path('tmp/regulations_formatted')

    regulation_title_list = [doc['title'] for doc in db['regulations'].find({}, {'_id': 0, 'title': 1})]

    for regulation_file_path in regulations_folder_path.iterdir():
        if regulation_file_path.stem in regulation_title_list:
            print(f'Regulation {regulation_file_path.stem} already exists')
            continue
        import_regulation(db, regulation_file_path)
        import_entry(db, formatted_regulations_dir_path, regulation_file_path)

