import streamlit as st

st.set_page_config(page_title="Welcome to Sheepish Mentality 🐑", layout="centered")

st.markdown("""
    <h1 style='text-align: center;'>🐑🐑🐑</h1>
    <h2 style='text-align: center;'>Welcome to Sheepish Mentality!</h2>
    <p style='text-align: center;'>🤪💭 (win by being a follower... or the one worth following!)</p>
""", unsafe_allow_html=True)

st.title("🐏 Sheepish Mentality 🐑🧠🤣🌾 - Multiplayer Game")
st.subheader("Play together in real time with your friends!")

col1, col2 = st.columns(2)
with col1:
    st.page_link("Rules.py", label="📜 View Rules", icon="📖")
with col2:
    st.page_link("Play.py", label="🎮 Start Playing", icon="🎮")