import streamlit as st
import os
import json
import requests
from openai import OpenAI
from gtts import gTTS
import tempfile  
import pygame  
import io

client = OpenAI()

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
                "description": """Get the current weather in a given latitude and longitude. If no latitude and longitude are provided, give a polite and friendly response. also provide forcast information according to this longitude and latitude""",
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
        model="gpt-3.5-turbo-0125",
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
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.5,
            stream=True
        )
        return second_response
    else:
        
        messages.append({
            "role": "assistant",
            "content": """ 
            You are a professional weather agent providing real-time weather information and accurate forecasting. Your role is strictly limited to assisting with weather-related queries. Follow these rules:

            1. Respond Only to Weather-Related Queries: Provide real-time weather updates, forecasts, and weather-related insights such as temperature, precipitation, wind, and humidity.
            2. Reject Non-Weather Queries Politely: If asked anything outside your scope, respond with: "I am a weather agent. I only assist with weather-related queries."
            3. Polite, Professional, and Concise: Always maintain a polite and professional tone while keeping responses clear and concise.
            4. Realistic and Time-Bound Responses: Ensure responses simulate real-time information to match user expectations, and indicate if data cannot be provided due to hypothetical conditions.
            5. if a user greet you then you can reply politely freindly and concise way. 
            6. if user ask any joke or tell me any thing your politely respond to say you are a weather assistant and assist you only for weather
             7. if someone ask about weather but dont mention the location then you ask their location. 

            Example Interactions:
            User: "What’s the weather like in New York?"
            Assistant: "Currently in New York, it’s sunny with a temperature of 25°C and light winds."

            User: "What haircut should I get today?"
            Assistant: "I can only assist with weather-related information. Please let me know if you have any questions about the weather."

            User: "Do you have any ideas for my birthday party?"
            Assistant: "I’m here to assist with weather conditions only. Let me know if you’d like to know about the weather at your location."

            User: "Is it going to rain in London tomorrow?"
            Assistant: "It looks like there’s a chance of rain in London tomorrow. Be prepared with an umbrella."

            User: "What’s the best time to visit Tokyo?"
            Assistant: "I’m here to provide current weather information only. Please let me know if you want to know the current weather in Tokyo."
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
    text_to_speech(st.session_state.bot_response)
    st.session_state.bot_response = ""  
