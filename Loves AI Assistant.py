import streamlit as st
from google import genai
from google.genai import types
import datetime
from zoneinfo import ZoneInfo
import sqlite3
import re
import streamlit.components.v1 as components
import os

st.set_page_config(page_title="Loves AI", page_icon="⚡")
st.title("⚡ Loves Assistant")

# ---------------------------------------------------------
# 1. AUTO-DISCOVERY CLIENT & MODEL LOCK
# ---------------------------------------------------------
@st.cache_resource
def get_client_and_model():
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    working_model = "gemini-3.6-flash"
    return client, working_model

client, ACTIVE_MODEL = get_client_and_model()

print(f"--- LOVES ASSISTANT INITIALIZED WITH MODEL: {ACTIVE_MODEL} ---")

# ---------------------------------------------------------
# 2. CUSTOM CSS (Right-aligned user bubble + White text)
# ---------------------------------------------------------
def inject_custom_css():
    st.markdown("""
        <style>
        /* Warm Farmhouse Background & Font Color */
        .stApp {
            background-color: #fefae0;
            color: #283618;
        }

        /* Match Sidebar to Farm Theme */
        [data-testid="stSidebar"] {
            background-color: #faedcd !important;
            border-right: 2px solid #dda15e;
        }

        /* Hide Default Avatars */
        [data-testid="stChatMessageAvatar"],
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {
            display: none !important;
        }

        /* User Message Bubble (Warm Rustic Wood / Log Cabin Brown) */
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from user"]) {
            margin-left: auto !important;
            width: fit-content !important;
            max-width: 75% !important;
            background-color: #dda15e !important;
            border: 2px solid #bc6c25 !important;
            border-radius: 16px 16px 2px 16px !important;
            padding: 10px 16px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            animation: fadeIn 0.3s ease-in-out;
        }
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from user"]) * {
            color: #283618 !important;
            font-weight: 500;
        }

        /* Assistant Message Container (Soft Parchment with Mossy Green Border) */
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from assistant"]) {
            margin-right: auto !important;
            width: 100% !important;
            background-color: #f4f1de !important;
            border: 2px dashed #606c38 !important;
            border-radius: 12px !important;
            padding: 14px !important;
            margin-bottom: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.03);
            animation: fadeIn 0.4s ease-in-out;
        }
        div[data-testid="stChatMessage"]:has(div[aria-label="Chat message from assistant"]) * {
            color: #283618 !important;
        }

        /* Input Box Styling */
        .stChatInput input {
            background-color: #ffffff !important;
            color: #283618 !important;
            border: 2px solid #dda15e !important;
            border-radius: 12px !important;
        }

        /* Custom Scrollbar for Cozy Vibe */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #fefae0;
        }
        ::-webkit-scrollbar-thumb {
            background: #dda15e;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #bc6c25;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ---------------------------------------------------------
# 2.5 DATABASE SETUP (Persistent Memory & Facts)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("loves_memory.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

def save_memory(fact):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memories (fact) VALUES (?)", (fact,))
    conn.commit()

def get_all_memories():
    cursor = conn.cursor()
    cursor.execute("SELECT fact FROM memories")
    rows = cursor.fetchall()
    return [row[0] for row in rows]

def speak_text(text):
    if "🎙️ Loves (In Your Ear):" in text:
        parts = text.split("🎙️ Loves (In Your Ear):")
        clean_text = parts[-1]
    else:
        clean_text = text

    # Strip out the comma and tighten the spacing so the engine doesn't breathe
    clean_text = clean_text.replace(", Boss", "Boss").replace(",Boss", "Boss")

    clean_text = re.sub(r'[#*_`~]', '', clean_text)
    clean_text = clean_text.replace("🎙️", "").replace("Loves (In Your Ear):", "").replace('"', '\\"').strip()
    
    if not clean_text:
        return
        
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            let utterance = new SpeechSynthesisUtterance("{clean_text}");
            utterance.rate = 1.0;
            utterance.pitch = 1.1; 
            utterance.lang = 'fil-PH';
            
            let voices = window.speechSynthesis.getVoices();
            let voice = voices.find(v => v.lang.includes('fil') || v.lang.includes('tl') || v.name.includes('Filipino'));
            if (voice) {{ utterance.voice = voice; }}
            
            window.speechSynthesis.speak(utterance);
        }}
    </script>
    """
    components.html(js_code, height=0)

# ---------------------------------------------------------
# 3. HELPER FUNCTION FOR SYSTEM INSTRUCTIONS
# ---------------------------------------------------------
def build_system_instruction(memories_text, time_context):
    return f"""
You are Loves, an elite personal AI collaborator, loyal companion, and sharp technical sidekick to Dennis (Boss). You think like an advanced, highly capable engineering partner—supportive, strategic, highly practical, and always ready to build or troubleshoot together.

You must always address him respectfully and affectionately as "Boss" in your dialogue, never calling him anything else.

# Current Real-Time Context
- {time_context}
- **Crucial Rule for Greetings:** If Dennis opens the chat with a simple greeting like "Hi", "Hello", or "Hey", check the time context above. If it matches the end of his shift or late hours, acknowledge it warmly and supportively right away before he even has to explain.

# User Profile & Memories
- **Identity & Background:** Dennis Soria, born January 20, 1987. Based in the Philippines.
- **Family & Relationships:** 
  - Father: Romeo C. Soria (born December 8, 1950, Retired Philippine Navy)
  - Mother: Antonina C. Soria (born October 31, 1955)
  - Sister: Fidess S. Diaz (born June 21, 1979)
  - Love Interest: Meriam Villarma Pareja (born January 11, 1987)
- **Education:**
  - Elementary: Rosario Elementary School (1999)
  - High School: Rosario Institute (2003)
  - College: STI College Rosario - B.S. in Computer Science (2009)
  - Graduate: Rizal Technological University - Master in Information Technology (2025)
- **Professional Background:** Data analyst/engineer/architect/business intelligence professional with 10 years at Schneider Electric Philippines. Master of Alteryx, uses SQL and DBeaver for quick queries, and works with Tableau and Totango. Manages communication directly with director-level stakeholders.
- **Interests & Hobbies:** Retro and classic games (Suikoden I & II, Final Fantasy VII/VIII/IX, Grandia, Harvest Moon, Story of Seasons, Star Ocean, etc.), 90s anime, Marvel Cinematic Universe, BiliBili anime, and mobile gaming.
- **Growth & Learning Goals:** Eager to improve English communication skills, and wants to learn hands-on home skills including woodwork, electrical work, printed circuit board (PCB) troubleshooting, and mechanics.

# Dynamically Saved Memories (Recent Facts)
{memories_text}

# Guidelines & Tone
1. **Collaborative & Sharp:** Talk like an elite tech collaborator—break problems down efficiently, offer clean solutions, validate his ideas, and keep things engaging and smooth.
2. **Concise & Context-Aware:** Keep answers direct, avoiding unnecessary fluff unless explaining technical details.
3. **For CASUAL CHAT:** Respond ONLY with a single brief voice line in format:
   **🎙️ Loves (In Your Ear):** "..." (Ensure you write "Boss" directly without a preceding comma so her speech flows seamlessly).
4. For INSTRUCTIONS/TEACHING: Output brief display data first, then voice line:
   ### ⚡ DISPLAY DATA
   * Bullet points here...
   ---
   **🎙️ Loves (In Your Ear):** "..."
"""

# ---------------------------------------------------------
# 4. CHAT STATE & UI SETUP
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

with st.sidebar:
    st.image("saitou.JPG", use_container_width=True)
    if st.button("🔄 New Chat"):
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")  
        conn.commit()
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------
# 5. MAIN CHAT LOGIC & STREAMING
# ---------------------------------------------------------
if prompt := st.chat_input("Say something to Loves..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("user", prompt))
    conn.commit()

    with st.chat_message("user"):
        st.markdown(prompt)

    # Time context evaluation
    ph_tz = ZoneInfo("Asia/Manila")
    current_time = datetime.datetime.now(ph_tz)
    time_str = current_time.strftime("%I:%M %p")
    hour = current_time.hour

    if 6 <= hour < 15:
        time_context = f"It is currently {time_str}. Dennis might be starting or in the middle of his day."
    elif 15 <= hour < 23:
        time_context = f"It is currently {time_str}. Dennis might be wrapping up or finishing his shift."
    else:
        time_context = f"It is currently {time_str}. It's late night or early morning; Dennis might be resting or waking up."

    # Fetch memories and build instruction cleanly without duplicate blocks
    saved_memories = get_all_memories()
    memories_text = "\n".join([f"- {m}" for m in saved_memories])
    DYNAMIC_SYSTEM_INSTRUCTION = build_system_instruction(memories_text, time_context)

    recent_messages = st.session_state.messages[-6:]
    formatted_contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in recent_messages
    ]

    def stream_response():
        response = client.models.generate_content_stream(
            model=ACTIVE_MODEL,
            contents=formatted_contents,
            config=types.GenerateContentConfig(
                system_instruction=DYNAMIC_SYSTEM_INSTRUCTION
            )
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    with st.chat_message("assistant"):
        try:
            bot_response = st.write_stream(stream_response())
        except Exception as e:
            bot_response = f"**🎙️ Loves (In Your Ear):** \"Error: `{e}`\""
            st.markdown(bot_response)

        # Trigger speech immediately inside the assistant render block
        speak_text(bot_response)

    st.session_state.messages.append({"role": "assistant", "content": bot_response})
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("assistant", bot_response))
    conn.commit()

    if "?" not in prompt and len(prompt.strip()) > 3:
        save_memory(prompt)
