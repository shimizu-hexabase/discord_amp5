import os
import openai
import discord
from dotenv import load_dotenv
import base64
import aiohttp
from webserver import server_thread

# 別ファイルからメッセージ関数をインポート
from SystemMessage import getSystemMessage
from FFCMessage import getFFCMessage
from CGCMessage import getCGCMessage

# Variables
NAME = "HEXABASE APP MODELER"
VER = "APP MODELER PROMPTER 5(AMP5)"
CURRENT_DATE = "2024"
MODEL = "gpt-4o-2024-08-06"  # 指定されたモデル
CONTEXT_WINDOW = 128000
MAX_OUTPUT_TOKENS = 16000
TRAININGDATA_CUTOFF = "Oct 2023"

# 環境変数の読み込み
load_dotenv()
api_key = os.getenv('OPENAI_APIKEY')
token = os.getenv('DISCORD_TOKEN')
openai.api_key = api_key

# Botのインテント設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # メッセージ内容の取得を有効にする

# Botクライアントの初期化
client = discord.Client(intents=intents)

# 初期メッセージの取得
system_message = getSystemMessage()
ffc_message = getFFCMessage()
cgc_message = getCGCMessage()

# スレッド内で`/amp5`が打たれたことを記録するセット
amp5_invoked_threads = set()
thread_conversation_logs = {}


# OpenAI APIを使ったメッセージ応答
def generate_openai_response(conversation_log):
  try:
    # 最初に追加するシステムおよび初期メッセージ
    initial_messages = [{
        "role": "system",
        "content": system_message
    }, {
        "role": "user",
        "content": ffc_message
    }, {
        "role": "assistant",
        "content": "了解"
    }, {
        "role": "user",
        "content": cgc_message
    }, {
        "role": "assistant",
        "content": "了解"
    }]

    # 既存の会話ログに最初のメッセージを追加
    conversation_log = initial_messages + conversation_log

    # ampコマンドの省略
    for message in conversation_log:
      if 'content' in message and isinstance(message['content'], str):
        message['content'] = message['content'].replace('/amp5', '').strip()

    # ログに送信内容を表示
    print(f"\n---- OpenAIリクエスト ----\n")
    for message in conversation_log:
      print(f"Role: {message['role']}, Content: {message['content'][:100]}"
            )  # 100文字まで表示

    response = openai.ChatCompletion.create(model=MODEL,
                                            messages=conversation_log,
                                            max_tokens=MAX_OUTPUT_TOKENS,
                                            temperature=0.7,
                                            request_timeout=300)
    return response.choices[0].message['content']
  except Exception as e:
    print(f"OpenAI APIエラー: {e}")
    return "エラーが発生しました。応答できません。"


# URLから画像をbase64エンコードする関数
async def encode_image_from_url(url):
  async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
      if response.status == 200:
        image_bytes = await response.read()
        return base64.b64encode(image_bytes).decode('utf-8')
  return None


@client.event
async def on_ready():
  print(f'{client.user} が接続されました！')
  print(f'アプリ名: {NAME}, バージョン: {VER}, 年: {CURRENT_DATE}')


@client.event
async def on_message(message):
  if message.author == client.user:
    return  # 自分自身のメッセージは無視

  # メッセージの内容をコンソールに出力
  print(f"受信メッセージ: {message.content} (送信者: {message.author})")

  async def handle_thread_response(thread, user_message_content,
                                   original_message):
    conversation_log = []
    thread_id = thread.id

    # スレッド元の投稿を取得してチェック
    if thread.parent:
      try:
        parent_message = await thread.parent.fetch_message(thread.id)
        if parent_message and parent_message.content:  # 空のメッセージを除外
          print(f"スレッドの親メッセージを取得しました: {parent_message.content}")
          if '/amp5' in parent_message.content.lower():
            amp5_invoked_threads.add(thread_id)  # スレッド元で/amp5が打たれた場合に記録
          role = "assistant" if parent_message.author.bot else "user"
          thread_conversation_logs.setdefault(thread_id, [])
          thread_conversation_logs[thread_id].append({
              "role":
              role,
              "content":
              parent_message.content
          })
      except discord.NotFound:
        print("スレッドの親メッセージが見つかりませんでした。")
      except discord.Forbidden:
        print("スレッドの親メッセージの取得が許可されていません。")
      except discord.HTTPException as e:
        print(f"HTTPエラー: {e}")

    # 会話ログ新規作成
    thread_conversation_logs[thread_id] = []

    # スレッド内のすべてのメッセージ履歴を取得
    async for msg in thread.history(limit=100, oldest_first=True):
      content = msg.content
      if content:  # 空のメッセージをスキップ
        role = "assistant" if msg.author.bot else "user"
        thread_conversation_logs[thread_id].append({
            "role": role,
            "content": content
        })

      # `/amp5`のチェックと記録
      if '/amp5' in msg.content.lower():
        amp5_invoked_threads.add(thread_id)

    # メッセージ内容を会話ログに追加（最後のログと重複しない場合のみ）
    if user_message_content:
      if not thread_conversation_logs[thread_id] or \
         thread_conversation_logs[thread_id][-1]["content"] != user_message_content:
        thread_conversation_logs[thread_id].append({
            "role":
            "user",
            "content":
            user_message_content
        })

    # 画像が添付されている場合の処理
    if original_message.attachments:
      await original_message.add_reaction('💬')  # 画像の場合もリアクションを追加
      for attachment in original_message.attachments:
        if attachment.content_type and attachment.content_type.startswith(
            'image/'):
          print(f"画像が検出されました: {attachment.url}")

          # 画像をbase64エンコード
          base64_image = await encode_image_from_url(attachment.url)
          if base64_image:
            content = [{
                "role":
                "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message_content or "画像について説明して"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }]
            response = generate_openai_response(content)
            # 2000文字制限の分割処理を追加
            if len(response) > 2000:
              for chunk in [
                  response[i:i + 2000] for i in range(0, len(response), 2000)
              ]:
                await thread.send(chunk)
            else:
              await thread.send(response)

            await original_message.remove_reaction('💬', client.user
                                                   )  # 処理後にリアクションを削除
          else:
            await thread.send("画像の処理に失敗しました。")
            await original_message.remove_reaction('💬', client.user
                                                   )  # エラー時もリアクションを削除
          return  # 画像がある場合、他の処理をスキップ

    # テキストメッセージへの通常の応答
    await original_message.add_reaction('💬')
    response = generate_openai_response(thread_conversation_logs[thread_id])
    thread_conversation_logs[thread_id].append({
        "role": "assistant",
        "content": response
    })

    # 2000文字制限の分割処理を追加
    if len(response) > 2000:
      for chunk in [
          response[i:i + 2000] for i in range(0, len(response), 2000)
      ]:
        await thread.send(chunk)
    else:
      await thread.send(response)

    await original_message.remove_reaction('💬', client.user)

    # `/amp5`が打たれたスレッドとして記録
    amp5_invoked_threads.add(thread_id)

  # スレッド外での /amp5 コマンド処理
  if isinstance(message.channel, discord.TextChannel):
    if message.content.lower().startswith('/amp5'):
      user_message_content = message.content[len('/amp5'):].strip() or " "
      thread_name = user_message_content if user_message_content != " " else "(テキスト無し)"
      thread = await message.create_thread(name=thread_name)
      await handle_thread_response(thread, user_message_content, message)
    else:
      print("ボットコマンドが見つかりません。応答しません。")

  # スレッド内での処理
  elif isinstance(message.channel, discord.Thread):
    thread_id = message.channel.id
    if thread_id in amp5_invoked_threads:
      # `amp5_invoked_threads`に記録されているスレッドでは通常応答
      await handle_thread_response(message.channel, message.content, message)
    else:
      # スレッド元の投稿を含めて`/amp5`の存在を確認
      if message.channel.parent:
        try:
          parent_message = await message.channel.parent.fetch_message(
              message.channel.id)
          if parent_message and '/amp5' in parent_message.content.lower():
            print(f"スレッド {thread_id} の元のメッセージに`/amp5`が含まれています。")
            amp5_invoked_threads.add(thread_id)
            await handle_thread_response(message.channel, message.content,
                                         message)
            return
        except discord.NotFound:
          print("スレッドの親メッセージが見つかりませんでした。")
        except discord.Forbidden:
          print("スレッドの親メッセージの取得が許可されていません。")
        except discord.HTTPException as e:
          print(f"HTTPエラー: {e}")

      # 過去のメッセージ履歴を確認
      async for msg in message.channel.history(limit=100, oldest_first=True):
        if '/amp5' in msg.content.lower():
          print(f"スレッド {thread_id} にて過去に`/amp5`が打たれています。")
          amp5_invoked_threads.add(thread_id)
          await handle_thread_response(message.channel, message.content,
                                       message)
          return
      print("このスレッドでは`/amp5`が打たれていません。応答しません。")


if __name__ == "__main__":
  print("Starting FastAPI server thread...")  # 追加: サーバー起動前のログ
  server_thread()  # FastAPIサーバーを起動
  print("FastAPI server thread started.")  # 追加: サーバー起動後のログ
  try:
    print("Starting Discord bot...")  # 追加: Discordボットの起動ログ
    client.run(token)  # Discordボットの実行
  except Exception as e:
    print(f"Botの実行中にエラーが発生しました: {e}")
    os.system("kill 1")
