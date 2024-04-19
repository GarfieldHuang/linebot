# my_linebot.py
# Create a new virtual environment
# python -m venv env

# Activate the virtual environment
# env\Scripts\activate
# cd .\linebot_aoai\
# python my_linebot.py

from flask import Flask, request, abort
import os
# import openai
# from openai import OpenAI
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
# import pkg_resources
from openai import AzureOpenAI

# openai_version = pkg_resources.get_distribution("openai").version
# print(openai_version)
# Set OpenAI API details
# openai.api_type = "azure"
# openai.api_version = "2024-02-01"
# openai.api_key = os.getenv("OPENAI_API_KEY")
# openai.api_base = os.getenv("OPENAI_API_BASE")

client = AzureOpenAI(
    azure_endpoint = os.getenv("OPENAI_API_BASE"), 
    api_key = os.getenv("OPENAI_API_KEY"),  
    api_version="2024-02-01"
)
app = Flask(__name__)

# Initialize messages list with the system message
messages = [
    {"role": "system", "content": "You are a helpful assistant . \
                                   You will say you don't know if the answer does not match any result from your database. Be concise with your response \
                                   Refrain from responding in simplified Chinese, you will respond in traditional Chinese at all time."},
]

# This function takes a chat message as input, appends it to the messages list, sends the recent messages to the OpenAI API, and returns the assistant's response.
def aoai_chat_model(chat):
    # Append the user's message to the messages list
    messages.append({"role": "user", "content": chat})

    # Only send the last 5 messages to the API
    recent_messages = messages[-5:]

    # Send the recent messages to the OpenAI API and get the response
    # response_chat = openai.ChatCompletion.create(
    #     engine="gpt-4",
    #     messages=recent_messages,
    #     temperature=0.7,
    #     max_tokens=150,
    #     top_p=0.95,
    #     frequency_penalty=0,
    #     presence_penalty=0,
    #     stop=None
    # )
    response_chat = client.chat.completions.create(
        model="gpt4", #要用部屬名稱，不是模型名稱
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Refrain from responding in simplified Chinese, you will respond in traditional Chinese at all time."
            },
            {
                "role": "user",
                "content": recent_messages[-1]['content'],
            }
        ],
        temperature=0.7
    )

    # Append the assistant's response to the messages list
    messages.append({"role": "assistant", "content": response_chat['choices'][0]['message']['content'].strip()})

    return response_chat['choices'][0]['message']['content'].strip()

# Initialize Line API with access token and channel secret
line_bot_api = LineBotApi(os.getenv('LINE_ACCESS_TOKEN'))
handler1 = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# This route serves as a health check or landing page for the web app.
@app.route("/")
def mewobot():
    return '測試!!!'

# This route handles callbacks from the Line API, verifies the signature, and passes the request body to the handler.
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler1.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# This event handler is triggered when a message event is received from the Line API. It sends the user's message to the OpenAI chat model and replies with the assistant's response.
@handler1.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=aoai_chat_model(event.message.text))
    )

if __name__ == "__main__":
    app.run()
