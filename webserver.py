from threading import Thread

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Server is Online."}

def start():
    # ポートを環境変数PORTから取得（Koyebが設定する）
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

def server_thread():
    t = Thread(target=start)
    t.start()
