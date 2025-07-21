import streamlit as st
import random
import time
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from difflib import SequenceMatcher
import json
from streamlit_autorefresh import st_autorefresh

# --- Initialise Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_creds"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["fire_db_url"]
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


def set_herd_result(room_id, herd_data):
    if herd_data is not None:
        db.reference(f"herd_rooms/{room_id}/herd_result").set(herd_data)
    else:
        db.reference(f"herd_rooms/{room_id}/herd_result").delete()


def get_herd_result(room_id):
    return db.reference(f"herd_rooms/{room_id}/herd_result").get()


# --- Herd Group Detection ---
def get_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_herd_group(answers, threshold=0.75):
    grouped_answers = {}
    for player, answer in answers.items():
        matched = False
        for key in grouped_answers:
            if get_similarity(answer, key) >= threshold:
                grouped_answers[key].append(player)
                matched = True
                break
        if not matched:
            grouped_answers[answer] = [player]

    if not grouped_answers:
        return None

    sorted_groups = sorted(grouped_answers.items(), key=lambda x: len(x[1]), reverse=True)
    if len(sorted_groups) < 1:
        return None

    top_size = len(sorted_groups[0][1])
    top_groups = [group for group in sorted_groups if len(group[1]) == top_size]

    if len(top_groups) == 1 and top_size > 1:
        return top_groups[0][0], top_groups[0][1]
    else:
        return "TIE", grouped_answers


# --- Question Bank ---
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # goes up from /pages to root


def load_question_bank():
    def load_json(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error loading {filename}: {e}")
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

# Auto-refresh for non-hosts to update the question
if room_id and player_name and not is_host:
    st_autorefresh(interval=3000, key="auto-refresh")  # Refresh every 3 seconds

if room_id and player_name:
    if is_host:
        if st.button("🎲 Generate Question"):
            if st.session_state.question_bank:
                question_data = random.choice(st.session_state.question_bank)
                st.session_state.question_bank.remove(question_data)
            else:
                question_data = {"type": "open", "question": "What's your favourite food?"}  # Fallback question
            set_question(room_id, question_data)
            set_herd_result(room_id, None)  # clear previous herd result
            st.success("New question set for the room!")

    question_data = get_question(room_id)
    if question_data:
        question_text = question_data if isinstance(question_data, str) else question_data.get("question", "")
        st.markdown(f"### Question: **{question_text}**")

        if isinstance(question_data, dict):
            if question_data.get("type") == "mc" and "options" in question_data:
                player_answer = st.radio("Choose your answer:", question_data["options"], key="mc")
            elif question_data.get("type") == "pick":
                current_players = list(get_player_list(room_id).keys())
                player_answer = st.radio("Pick a player among us:", current_players, key="pick")
            else:
                player_answer = st.text_input("Your Answer")
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
                    herd_data = {}
                    if herd_result and herd_result[0] != "TIE":
                        herd_answer, herd_players = herd_result
                        herd_data = {
                            "herd_answer": herd_answer,
                            "herd_players": herd_players,
                            "answers": answers,
                            "scores": {}
                        }
                        for player, answer in answers.items():
                            if player in herd_players:
                                increment_score(room_id, player)
                                herd_data["scores"][player] = "✅"
                            else:
                                herd_data["scores"][player] = "❌"
                    else:
                        herd_data = {
                            "herd_answer": None,
                            "herd_players": [],
                            "answers": answers,
                            "scores": {player: "❌" for player in answers},
                            "message": "Too many leaders, not enough sheep! 🐑"
                        }
                    set_herd_result(room_id, herd_data)
                else:
                    st.warning("Need at least 2 answers to determine the herd.")

            if st.button("Clear Room (Host Only)"):
                clear_room(room_id)
                set_herd_result(room_id, None)
                st.success("Room cleared. Ready for new round.")

        # Display herd result for everyone if available
        herd_data = get_herd_result(room_id)
        if herd_data:
            if herd_data.get("herd_answer"):
                st.markdown(f"### 🧠 Herd Answer: **{herd_data['herd_answer']}**")
            else:
                st.markdown("### 🧠 Herd Answer: **None! Everyone disagreed!**")
                if herd_data.get("message"):
                    st.markdown(f"**{herd_data['message']}**")

            for player, answer in herd_data["answers"].items():
                result = herd_data["scores"].get(player, "❌")
                st.write(f"{player}: {answer} {result}")

            st.markdown("---")
            st.markdown("### 🏆 Scoreboard")
            scores = get_scores(room_id)
            sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
            for player, score in sorted_scores:
                st.write(f"{player}: {score} point(s)")

        st.markdown("---")
        st.markdown("### 👥 Players in Room")
        players = get_player_list(room_id)
        for player in players:
            st.write(f"- {player}")
    else:
        st.info("No question has been set for this room yet.")
else:
    st.warning("Please enter both room code and your name to play.")
