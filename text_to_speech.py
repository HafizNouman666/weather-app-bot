import streamlit as st
import os
import json
import requests
from openai import OpenAI
from gtts import gTTS
from dotenv import load_dotenv
import tempfile  
import pygame  
import io

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

#function to fetch data from weather api
def get_current_weather(latitude, longitude):
    """Get the current weather in a given latitude and longitude"""
    base = "https://api.openweathermap.org/data/2.5/weather"
    key = os.environ.get('WEATHERMAP_API_KEY') 
    request_url = f"{base}?lat={latitude}&lon={longitude}&appid={key}&units=metric"
    response = requests.get(request_url)
    
    if response.status_code == 200:
        result = {
            "latitude": latitude,
            "longitude": longitude,
            **response.json()["main"]
        }
        return json.dumps(result, indent=4)
    else:
        return f"Failed to fetch weather data. Status Code: {response.status_code}" 

def run_conversation(content):
    messages = [{"role": "user", "content": content}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": """Get the current weather in a given latitude and longitude and aslo give response.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "string", "description": "Latitude of a place"},
                        "longitude": {"type": "string", "description": "Longitude of a place"},
                    },
                    "required": ["latitude", "longitude"],
                },
            },
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        temperature=0.8,
        tool_choice="auto",
    )
    response_message = response.choices[0].message

    tool_calls = response_message.tool_calls
    

    if tool_calls:
        messages.append(response_message)
        available_functions = {"get_current_weather": get_current_weather}
        print("********************************TOOL IS CALL****************************************************")
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            function_to_call = available_functions.get(function_name)
            if function_to_call:
                function_response = function_to_call(
                    latitude=function_args.get("latitude"),
                    longitude=function_args.get("longitude"),
                )
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })

        second_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            stream=True
        )
        return second_response
    else:
        print("-----------------------------------------TOOL NOT CALL----------------------------------------------------------")
        messages.append({
            "role": "assistant",
            "content": """ 
            You are a professional weather agent providing real-time weather information and accurate forecasting but you are also polite agent and do friendly conversation with user.
            1. if user ask about the realtime weather ask the specific location. 
            """
        })

        fallback_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            stream=True
        )
        return fallback_response
    
#convert into text to speech    
def text_to_speech(text):
    """Convert text to speech and play it without using pygame."""
    try:
        tts = gTTS(text=text, lang="en")
        
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio_file:
            tts.save(temp_audio_file.name)
            
            # Play the audio in Streamlit
            st.audio(temp_audio_file.name , autoplay=True)
    
    except Exception as e:
        st.error(f"Error during TTS playback: {e}")

#Streamlit Application 
page_bg_img = """
  <style>
  [data-testid="stAppViewContainer"]{
    background-image: url("https://images.unsplash.com/photo-1500964757637-c85e8a162699?q=80&w=1806&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: local;
}

[data-testid="stHeader"] {
background: rgba(0,0,0,0);
}
  </style>
""" 
st.markdown(page_bg_img , unsafe_allow_html = True)

st.title("Weather Chatbot 🌦️")
st.write("Hi! 👋 Ask me about the weather")

if "message" not in st.session_state:
    st.session_state.message = []
if "query" not in st.session_state:
    st.session_state.query = ""

# Function to process user query
def handle_query():
    user_query = st.session_state.query.strip()
    if user_query:
        st.session_state.message.append({"role": "user", "content": user_query})

        response_stream = run_conversation(user_query)
        bot_response = ""
        if hasattr(response_stream, "__iter__"):  
            for chunk in response_stream:
                if chunk.choices[0].delta.content:  
                    bot_response += chunk.choices[0].delta.content

        st.session_state.message.append({"role": "assistant", "content": bot_response})

        st.session_state.bot_response = bot_response

        st.session_state.query = ""


with st.container():
    st.write("### Conversation:")
    for chat in st.session_state.message:
        if chat["role"] == "user":
            st.markdown(f"👤 **You**: {chat['content']}")
        else:
            st.markdown(f"🤖 **Bot**: {chat['content']}")

st.text_input(
    "Your Query:",
    placeholder="E.g., What's the weather in Islamabad?",
    key="query",
    on_change=handle_query
)

if "bot_response" in st.session_state and st.session_state.bot_response:
    #text_to_speech(st.session_state.bot_response)
    st.session_state.bot_response = ""  
