# 使用官方 Python 映像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製當前目錄內容到容器內的 /app 目錄
COPY . /app

# 設定 PYTHONPATH 環境變量
ENV PYTHONPATH "${PYTHONPATH}:/app/src"

# 安裝所需的 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 暴露應用程式的埠
EXPOSE 8000

# 設定啟動命令
CMD ["python", "src/web_viewer.py"]
