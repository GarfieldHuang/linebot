from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from openai import AzureOpenAI
import uvicorn
from azure.storage.blob import BlobServiceClient

# Create a new virtual environment
# python -m venv env
# Activate the virtual environment
# env\Scripts\activate
# cd .\linebot_aoai\
# python my_linebot.py

# Set OpenAI API details
client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_API_BASE"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-01"
)

# Create a BlobServiceClient object
blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))

# Fetch the container
container_name = os.getenv("AZURE_CONTAINER_NAME")
container_client = blob_service_client.get_container_client(container_name)

# Access the container properties
container_properties = container_client.get_container_properties()
print(f"Container name: {container_properties.name}")
print(f"Container last modified: {container_properties.last_modified}")

app = FastAPI()

system_prompt = "You are a helpful assistant. Refrain from responding in simplified Chinese, you will respond in traditional Chinese at all time."
# Initialize messages list with the system message
messages = [
    {"role": "system", "content": system_prompt},
]

# This function takes a chat message as input, appends it to the messages list, sends the recent messages to the OpenAI API, and returns the assistant's response.
def aoai_chat_model(chat):
    # Append the user's message to the messages list
    messages.append({"role": "user", "content": chat})

    # Only send the last 10 messages to the API
    recent_messages = messages[-10:]

    response_chat = client.chat.completions.create(
        model="gpt4",  # 要用佈署名稱，不是模型名稱
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": recent_messages[-1]['content'],
            }
        ],
        temperature=0.7
    )

    # Access the assistant's response using the methods of the ChatCompletion class
    assistant_message = response_chat.choices[0].message.content.strip()

    # Append the assistant's response to the messages list
    messages.append({"role": "assistant", "content": assistant_message})

    return assistant_message

# Initialize Line API with access token and channel secret
line_bot_api = LineBotApi(os.getenv('LINE_ACCESS_TOKEN'))
handler1 = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# This route serves as a health check or landing page for the web app.
@app.get("/")
def linebot():
    return '測試!!!'

# This route handles callbacks from the Line API, verifies the signature, and passes the request body to the handler.
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    app.logger.info("Request body: " + body.decode())
    try:
        handler1.handle(body.decode(), signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        raise HTTPException(status_code=400, detail="Invalid signature. Please check your channel access token/channel secret.")
    return 'OK'

# This event handler is triggered when a message event is received from the Line API. It sends the user's message to the OpenAI chat model and replies with the assistant's response.
@handler1.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=aoai_chat_model(event.message.text))
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
