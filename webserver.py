from threading import Thread
from fastapi import FastAPI
import uvicorn
import os  # osモジュールのインポート

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Server is Online."}

def start():
    # Koyebが設定する環境変数PORTを使用する
    port = int(os.getenv("PORT", 8000))  # 環境変数がない場合は8000をデフォルト値に
    uvicorn.run(app, host="0.0.0.0", port=port)

def server_thread():
    t = Thread(target=start)
    t.start()
