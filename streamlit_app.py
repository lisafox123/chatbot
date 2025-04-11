import streamlit as st
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from AI_RPG import get_lyrics_azlyrics,show_all

# 設定 Spotify API 金鑰
SPOTIFY_CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]

# 初始化 Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
))

# Streamlit UI
st.set_page_config(page_title="Moodify", page_icon="☁️")
st.title("☁️ Moodify ")
st.subheader("讓旋律輕輕擁抱你的心🎧")

# 使用者輸入
user_input = st.text_input("🌿Hope you're having a gentle and pleasant day! How are you feeling?")

if st.button("🎶 Song for you"):
    if user_input:
        # 搜尋歌曲或歌手
        story = show_all(user_input)
        user_input = "The Pilot </3"
        search_results = sp.search(q=user_input, type="track", limit=1)

        # 檢查是否有結果
        if search_results and search_results["tracks"]["items"]:
            st.subheader("🎼 推薦歌曲")
            # 設定兩首歌並排顯示
            cols = st.columns(2)  # 建立兩個列
            
            for i, track in enumerate(search_results["tracks"]["items"]):
                track_name = track["name"]
                artist_name = track["artists"][0]["name"]
                spotify_url = track["external_urls"]["spotify"]
            # 兩列佈局
            left_col, right_col = st.columns([1, 2])  # `iframe`: 1, `story.content`: 2

            with left_col:
                st.markdown(f'''
                    <iframe src="https://open.spotify.com/embed/track/{track["id"]}?utm_source=generator" 
                    width="100%" height="380" frameBorder="0" allow="encrypted-media"></iframe>
                ''', unsafe_allow_html=True)

            with right_col:
                st.write(story.content)
        else:
            st.warning("😢 找不到符合條件的歌曲，請試試不同的關鍵字。")
    else:
        st.error("請輸入音樂相關的問題！")
