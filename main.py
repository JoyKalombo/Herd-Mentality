import streamlit as st
import random
import time
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from difflib import SequenceMatcher

# --- Load Environment Variables ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL")

# --- Setup OpenAI Client ---
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY in .env")
if not model:
    raise ValueError("Missing OPENAI_MODEL in .env")

client = OpenAI(api_key=api_key)

# --- Initialise Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-creds.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")
    })



# --- Firebase Helpers ---
def set_question(room_id, question):
    db.reference(f"herd_rooms/{room_id}/question").set(question)

def get_question(room_id):
    return db.reference(f"herd_rooms/{room_id}/question").get()

def submit_answer(room_id, player_name, answer):
    db.reference(f"herd_rooms/{room_id}/answers/{player_name}").set(answer)

def get_all_answers(room_id):
    return db.reference(f"herd_rooms/{room_id}/answers").get() or {}

def clear_room(room_id):
    db.reference(f"herd_rooms/{room_id}").delete()

# --- AI Helpers ---
def get_ai_prompt():
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Generate a fun, simple party game question for a game like 'Herd Mentality'. Just return the question."},
            {"role": "user", "content": "Give me a prompt."}
        ]
    )
    return response.choices[0].message.content.strip()

def get_ai_answer(prompt):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Give a one- or two-word answer to the following question. Only reply with the likely most common or 'herd' answer."},
            {"role": "user", "content": f"{prompt}"}
        ]
    )
    return response.choices[0].message.content.strip()

# --- Utility for Fuzzy Matching ---
def clean(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text.strip().lower())

def is_match(a, b, threshold=0.8):
    return SequenceMatcher(None, clean(a), clean(b)).ratio() >= threshold

# --- Streamlit UI ---
st.title("🐮 Herd Mentality - Multiplayer")
st.subheader("Play together in real time with your friends!")

room_id = st.text_input("Enter Room Code (e.g., room123)")
player_name = st.text_input("Enter Your Name")
is_host = st.checkbox("I am the host")

if room_id and player_name:
    if is_host:
        if st.button("🎲 Generate Question"):
            question = get_ai_prompt()
            set_question(room_id, question)
            st.success("New question set for the room!")

    question = get_question(room_id)
    if question:
        st.markdown(f"### Question: **{question}**")
        player_answer = st.text_input("Your Answer")

        if st.button("Submit Answer"):
            submit_answer(room_id, player_name, player_answer.strip())
            st.success("Answer submitted!")

        if st.button("Get AI Answer") and is_host:
            ai_answer = get_ai_answer(question)
            submit_answer(room_id, "AI", ai_answer.strip())
            st.success(f"AI answered: {ai_answer}")

        if st.button("Reveal Herd Answer") and is_host:
            answers = get_all_answers(room_id)
            if len(answers) >= 2:
                cleaned = [clean(a) for a in answers.values()]
                herd_raw = max(set(cleaned), key=cleaned.count)
                herd_answer = next(original for original in answers.values() if clean(original) == herd_raw)

                st.markdown(f"### 🧠 Herd Answer: **{herd_answer}**")
                for player, answer in answers.items():
                    match = "✅" if is_match(answer, herd_answer) else "❌"
                    st.write(f"{player}: {answer} {match}")
            else:
                st.warning("Need at least 2 answers to determine the herd.")

        if st.button("Clear Room (Host Only)") and is_host:
            clear_room(room_id)
            st.success("Room cleared. Ready for new round.")
    else:
        st.info("No question has been set for this room yet.")
else:
    st.warning("Please enter both room code and your name to play.")