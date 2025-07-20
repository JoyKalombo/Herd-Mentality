import streamlit as st
import random
import time
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from difflib import SequenceMatcher
import json

# --- Initialise Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-creds.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")
    })

# --- Firebase Helpers ---
def set_question(room_id, question_data):
    db.reference(f"herd_rooms/{room_id}/question").set(question_data)

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

# --- Herd Group Detection ---
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
def load_question_bank():
    def load_json(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return []
    open_qs = load_json("questions-open_ended.json")
    mc_qs = load_json("questions-multiple_choice.json")
    pick_qs = load_json("questions-pick_a_player.json")
    return (
        [{"type": "open", "question": q} for q in open_qs] +
        [{"type": "mc", **q} for q in mc_qs] +
        [{"type": "pick", "question": q} for q in pick_qs]
    )

if "question_bank" not in st.session_state:
    st.session_state.question_bank = load_question_bank()

# --- Utility for Fuzzy Matching ---
def clean(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text.strip().lower())

# --- Streamlit UI ---
st.markdown("""
    <h1 style='text-align: center;'>🐑🐑🐑</h1>
    <h2 style='text-align: center;'>Welcome to Sheepish Mentality!</h2>
    <p style='text-align: center;'>🤪💭 (win by being a follower... or the one worth following!)</p>
""", unsafe_allow_html=True)

st.title("🐏 Sheepish Mentality 🐑🧠🤣🌾 - Multiplayer Game")
st.subheader("Play together in real time with your friends!")

room_id = st.text_input("Enter Room Code (e.g., room123...✨ creativity is allowed... I promise) 🌀")
player_name = st.text_input("Enter Your Name")
is_host = st.checkbox("I am the host")

if room_id and player_name:
    if is_host:
        if st.button("🎲 Generate Question"):
            if st.session_state.question_bank:
                question_data = random.choice(st.session_state.question_bank)
                st.session_state.question_bank.remove(question_data)
            else:
                question_data = {"type": "open", "question": "What's your favourite food?"}  # Fallback question
            set_question(room_id, question_data)
            st.success("New question set for the room!")

    question_data = get_question(room_id)
    if question_data:
        question_text = question_data if isinstance(question_data, str) else question_data.get("question", "")
        st.markdown(f"### Question: **{question_text}**")

        if isinstance(question_data, dict) and question_data.get("type") == "mc" and "options" in question_data:
            player_answer = st.radio("Choose your answer:", question_data["options"], key="mc")
        else:
            player_answer = st.text_input("Your Answer")

        if st.button("Submit Answer"):
            submit_answer(room_id, player_name, player_answer.strip())
            st.success("Answer submitted!")

        if is_host:
            if st.button("Reveal Herd Answer"):
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

            if st.button("Clear Room (Host Only)"):
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