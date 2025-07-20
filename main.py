import streamlit as st
import random
import time
import os
import re
import openai
from openai import OpenAI
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from difflib import SequenceMatcher
import json

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
    db.reference(f"herd_rooms/{room_id}/players/{player_name}").set(True)

def get_all_answers(room_id):
    return db.reference(f"herd_rooms/{room_id}/answers").get() or {}

def get_player_list(room_id):
    return db.reference(f"herd_rooms/{room_id}/players").get() or {}

def increment_score(room_id, player_name):
    ref = db.reference(f"herd_rooms/{room_id}/scores/{player_name}")
    current = ref.get() or 0
    ref.set(current + 1)

def get_scores(room_id):
    return db.reference(f"herd_rooms/{room_id}/scores").get() or {}

def clear_room(room_id):
    db.reference(f"herd_rooms/{room_id}/question").delete()
    db.reference(f"herd_rooms/{room_id}/answers").delete()

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

# --- Herd Group Detection (No AI) ---
def get_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_herd_group(answers, threshold=0.75):
    texts = list(answers.values())
    scores = [0] * len(texts)
    for i in range(len(texts)):
        for j in range(len(texts)):
            if i != j and get_similarity(texts[i], texts[j]) >= threshold:
                scores[i] += 1

    max_score = max(scores)
    if max_score == 0:
        return None
    herd_index = scores.index(max_score)
    herd_text = texts[herd_index]
    herd_players = [player for player, ans in answers.items() if get_similarity(ans, herd_text) >= threshold]
    return herd_text, herd_players

# --- Question Bank ---
def load_custom_questions():
    try:
        with open("custom_questions.json", "r") as f:
            return json.load(f)
    except:
        return []

@st.cache_data(show_spinner=False)
def get_cached_questions(n=20):
    return [get_ai_prompt() for _ in range(n)]

if "question_bank" not in st.session_state:
    questions = load_custom_questions()
    if not questions:
        st.warning("No custom questions found. Please add questions to 'custom_questions.json'")
    st.session_state.question_bank = questions


# --- Utility for Fuzzy Matching ---
def clean(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text.strip().lower())

# --- Streamlit UI ---
st.title("🐮 Herd Mentality - Multiplayer")
st.subheader("Play together in real time with your friends!")

room_id = st.text_input("Enter Room Code (e.g., room123)")
player_name = st.text_input("Enter Your Name")
is_host = st.checkbox("I am the host")

if room_id and player_name:
    if is_host:
        if st.button("🎲 Generate Question"):
            if st.session_state.question_bank:
                question = st.session_state.question_bank.pop(0)
            else:
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
                herd_result = get_herd_group(answers)
                if herd_result:
                    herd_answer, herd_players = herd_result
                    st.markdown(f"### 🧠 Herd Answer: **{herd_answer}**")
                    for player, answer in answers.items():
                        if player in herd_players:
                            increment_score(room_id, player)
                            st.write(f"{player}: {answer} ✅")
                        else:
                            st.write(f"{player}: {answer} ❌")
                else:
                    st.markdown("### 🧠 Herd Answer: **None! Everyone disagreed!**")
                    for player, answer in answers.items():
                        st.write(f"{player}: {answer} ❌")

                st.markdown("---")
                st.markdown("### 🏆 Scoreboard")
                scores = get_scores(room_id)
                sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
                for player, score in sorted_scores:
                    st.write(f"{player}: {score} point(s)")
            else:
                st.warning("Need at least 2 answers to determine the herd.")

        if st.button("Clear Room (Host Only)") and is_host:
            clear_room(room_id)
            st.success("Room cleared. Ready for new round.")

        st.markdown("---")
        st.markdown("### 👥 Players in Room")
        players = get_player_list(room_id)
        for player in players:
            st.write(f"- {player}")
    else:
        st.info("No question has been set for this room yet.")
else:
    st.warning("Please enter both room code and your name to play.")