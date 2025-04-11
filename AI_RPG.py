from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from rich import print as pprint
from langchain_mistralai import ChatMistralAI
import os
import getpass
from langgraph.graph import START, StateGraph,END
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from typing_extensions import TypedDict
import json
import random
import streamlit as st
# 設定API Key
def mistral_key(api_key=None):
    if api_key:
        os.environ["MISTRAL_API_KEY"] = api_key
    else:
        os.environ["MISTRAL_API_KEY"] = getpass("Tavily API key:\n")

# 從 secrets.toml 讀取
api_key = st.secrets["MISTRAL_API_KEY"]
mistral_key(api_key)
# 初始化模型
llm = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0,
    max_retries=2,
)

from bs4 import BeautifulSoup
from typing import Dict
import requests as rq
import re
def get_newsongs(token):
    url = "https://api.spotify.com/v1/search"
    headers = { "Authorization": f"Bearer {token}"}
    # genre:rock
    params = {"q":"one ok rock","market":"TW","type":"track","limit": 10}
    response = rq.get(url, headers=headers, params=params)
    search_results = response.json()
    print(search_results)
    search = search_results['tracks']['items']
    uri = []
    name = []
    num = random.randint(0,10)
    for result in search:
        if result:  # 檢查 playlist 是否為 None
                name.append(result.get('name'))
                uri.append(result["uri"])
        else:
            print("Playlist is None.")
    return name[num],uri[num]


def get_token():
    token_url = "https://accounts.spotify.com/api/token"
    headers = {
    "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials",
        "client_id": "fe6ef6c3ecf84073a8afdd24fefafb34",
        "client_secret": "9205fe50d23146ac888b6ab5e7167dd4",
    }
    response = rq.post(token_url, headers=headers, data=data)
    token_info = response.json()['access_token']
    return token_info

# get_newsongs(token = get_token())

def play(token,uri):
    headers = { "Authorization": f"Bearer {token}"}
    device_response = rq.get("https://api.spotify.com/v1/me/player/devices", headers=headers)
    url = "https://api.spotify.com/v1/me/player/play"
    data = {
    "uris": uri }

    response = rq.put(url, headers=headers, json=data)

    if response.status_code == 204:
        return("成功開始播放 🎶")
    else:
        return("播放失敗:", response.json())
    
def clean_text(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)
def get_lyrics_azlyrics(artist, song):
    artist = clean_text(artist.replace(" ", "").lower())
    song = clean_text(song.replace(" ", "").lower())
    
    url = f"https://www.azlyrics.com/lyrics/{artist}/{song}.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = rq.get(url, headers=headers)
    if response.status_code != 200:
        return "歌詞未找到"

    soup = BeautifulSoup(response.text, "html.parser")
    br_tags = soup.find_all("br")
    # 提取 <br> 標籤前的文字
    br_texts = [
    br.previous_sibling.strip()
    for br in br_tags
    if br.previous_sibling and isinstance(br.previous_sibling, str)
    ]
    # 顯示結果
    br_texts = " ".join(br_texts)
    return br_texts

# 測試

class GraphState(TypedDict):
    question: str
    lyrics:str
    story:str
    chat_history:list[str]

def first_router(state):
    chat_history = state["chat_history"]
    question = state["question"]
    template = ChatPromptTemplate([
    ("system", """你是一個善於分辨問題的router，根據使用者的問題以及聊天紀錄
     分辨問題應該要自行回答還是導向下一個路徑
     ### **輸出格式**
    json：{{"datasource": "<yes | no>"}}"""),
    ("human", """根據使用者的問題{question}，以及歷史紀錄：{chat_history}來分配路徑。
     若使用者的問題與情緒無關(例如：詢問歷史紀錄相關內容)，- 僅返回 JSON: {{ "datasource": "no" }}
     若使用者的問題與情緒有關或想要推薦歌曲，- 僅返回 JSON: {{ "datasource": "yes" }}"""
)])
    prompt_value = llm.invoke(
    {
        "question": question,
        "chat_history": chat_history
    }
)
    source = json.loads(source.content)["datasource"]
    print(source)
    if source == "yes":
        return "yes"
    else:
        return "no"
def general(state):
    question = state["question"]

    
def route_question(state):
    """
    分辨問題的去向(以檢索為主)
    """
    print("---ROUTE QUESTION---")
    question = state["question"]
    router_instructions = """
    你是一個善於分辨文字情緒的專家。
    請根據使用者的訊息情緒選擇要推薦什麼類型的歌給他。
    必要時檢索聊天紀錄取得資訊。
    - **向量資料庫（vectorstore）**：包含所有聊天紀錄取得使用者資訊。  
    - **新的歌曲（new）**：當使用者想要創新一點或特定情緒的歌時。  
    - **喜歡的歌（like）**：當使用者指定要自己喜歡的歌時。  
    !不要包含额外的推理或解释。专注于识别回答用户问题的文档。
    
    ### **輸出格式**
    json：{{"datasource": "<vectorstore | new | like>"}}

    **請確保輸出只有 JSON，避免任何額外解釋或非 JSON 內容。**
    """
    router_prompt = """
    使用者的問題：{question}
    根據使用者的訊息，選擇要檢索聊天紀錄了解問題，還是直接從問題了解使用者情緒。
    你的回應必須是 **標準 JSON 格式**，無多餘內容，例如：
    1. **聊天紀錄取得使用者資訊**：  
       - 僅返回 JSON: {{ "datasource": "vectorstore" }}

    2. **創新的歌曲分享**（使用者想要創新一點或特定情緒的歌時）：  
       - 僅返回 JSON: {{ "datasource": "new" }}

    3. **喜歡的歌**（使用者指定要自己喜歡的歌時）：  
       - 僅返回 JSON: {{ "datasource": "like" }}

    - **請確保回應格式嚴格遵守 JSON 標準，避免額外解釋或非 JSON 輸出。**

    """
    source = llm.invoke(
            [SystemMessage(content=router_instructions)]
            + [
                HumanMessage(
                    content=router_prompt.format(
                        question=question
                    )
                )
            ]
        )
    source = json.loads(source.content)["datasource"]
    print(source)

    if source == "new":
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "new"
    elif source == "vectorstore":
        print("---ROUTE QUESTION TO RAG---")
        return "vectorstore"
    elif source == "like":
        print("---ROUTE QUESTION TO GENERAL---")
        return "like"

def ready_for_music(state):
    token = get_token()
    name,uri = get_newsongs(token)
    player = play(token,uri) 

def create_a_story(state):
    print("---CREATE A STORY---")
    lyrics = get_lyrics_azlyrics(artist = "ONE OK ROCK", song = "The Pilot </3")
    story_instructions = """
    你是一個很會用歌詞說故事的專家。
    請根據歌詞用繁體中文說一則與歌詞相關的故事
    """
    story_prompt = f"""
    歌詞：{lyrics}
    根據歌詞的含意，用繁體中文設計一則與該理念相關的故事
    最後在結尾的部分，用一句話說明這段故事想表達的
    """
    story = llm.invoke(
            [SystemMessage(content=story_instructions)]
            + [
                HumanMessage(
                    content=story_prompt
                )
            ]
        )
    print(story)
    return {"story":story}
    

workflow = StateGraph(GraphState)
workflow.add_node(create_a_story,"create_a_story")
workflow.add_node(general,"general")
workflow.set_conditional_entry_point(
        route_question,
        {
            "new": "create_a_story",
            "vectorstore": END,
            "like": END,
        },
    )
# workflow.add_conditional_edges(
#     first_router,
#         route_question,
#         {
#             "new": "create_a_story",
#             "vectorstore": END,
#             "like": END,
#         },
#     )
workflow.add_edge("create_a_story",END)
graph = workflow.compile()

def show_all(query):
    inputs = {
        "question": query,
        "max_retries": 2,
    }
    try:
        for output in graph.stream(inputs, stream_mode="values"):
            pprint(output)
        return output["story"]
    except Exception as e:
        print(f"發生錯誤: {str(e)}，請再輸入一次。")

# show_all(query="我今天心情很差")