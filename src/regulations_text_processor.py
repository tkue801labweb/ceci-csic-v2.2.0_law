import re
import pandas as pd
from pathlib import Path
from typing import Union

# === 讀取 Excel 中的對應表 ===
hierarchy_type_df = pd.read_excel("各法規階層.xlsx")
hierarchy_type_dict = dict(zip(hierarchy_type_df["檔案名稱"].str.replace(".txt", "", regex=False), hierarchy_type_df["階層類型"]))

# === 多層級 hierarchy pattern map（與 mongodb_import.py 相同）===
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


# === 判斷某行屬於哪一層 ===
def detect_hierarchy_level(text: str, file_name: str) -> int:
    hierarchy_type = hierarchy_type_dict.get(file_name)
    if not hierarchy_type or hierarchy_type not in hierarchy_pattern_map:
        return 0
    patterns_by_level = hierarchy_pattern_map[hierarchy_type]
    for i, pattern_list in enumerate(patterns_by_level):
        for pattern in pattern_list:
            if re.match(pattern, text):
                return i + 1  # 層級從 1 開始
    return 0

# === 處理法規 TXT 並加上正確 heading 等級 ===
def process_regulations_txt(input_file: Union[str, Path], output_file: Union[str, Path]) -> None:
    file_name = Path(input_file).stem
    with open(input_file, 'r', encoding='utf-8') as f:
        txt_lines = f.readlines()

    new_lines = []
    for line in txt_lines:
        stripped_line = line.strip()
        level = detect_hierarchy_level(stripped_line, file_name)
        if level > 0:
            line = '#' * level + ' ' + stripped_line + '\n'
        new_lines.append(line)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

# === 批次處理整個資料夾 ===
if __name__ == '__main__':
    regulations_dir_path = Path('data/regulations')
    output_dir_path = Path('tmp/regulations_formatted')
    output_dir_path.mkdir(parents=True, exist_ok=True)

    for txt_file in regulations_dir_path.glob('*.txt'):
        print(f'Processing {txt_file}...')
        output_file_path = output_dir_path / (txt_file.stem + '.md')
        process_regulations_txt(txt_file, output_file_path)
        print(f'Output file: {output_file_path}')

