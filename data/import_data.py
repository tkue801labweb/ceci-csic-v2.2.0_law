import os
import sys
from pathlib import Path

# 設定專案根目錄到 Python 路徑
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.mongodb_import import import_regulations, import_entry

if __name__ == "__main__":
    # 設定資料來源路徑
    regulations_folder_path = current_dir / "data" / "regulations"
    formatted_regulations_dir_path = current_dir / "tmp" / "regulations_formatted"
    
    # 執行資料匯入
    print("開始匯入法規資料...")
    import_regulations(regulations_folder_path)
    print("開始匯入條文資料...")
    import_entry(formatted_regulations_dir_path, regulations_folder_path)
    print("資料匯入完成!") 