from threading import Thread
from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Server is Online."}

def start():
    port = int(os.getenv("PORT", 8000))
    print(f"Starting FastAPI server on port {port}...")  # サーバー起動前のログ
    # サーバーを非ブロッキングで起動する
    server = uvicorn.Server(config=uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info"))
    Thread(target=server.run).start()  # 新しいスレッドで実行
    print("FastAPI server started.")  # サーバー起動後のログ

def server_thread():
    print("Initializing server thread...")  # サーバースレッドの初期化ログ
    t = Thread(target=start)
    t.start()
    print("Server thread initialized.")  # サーバースレッド初期化完了のログ
