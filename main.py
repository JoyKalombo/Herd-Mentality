import streamlit as st

# --- Streamlit UI ---
st.markdown("""
    <h1 style='text-align: center;'>🐑🐑🐑</h1>
    <h2 style='text-align: center;'>Welcome to Sheepish Mentality!</h2>
    <p style='text-align: center;'>🤪💭 (win by being a follower... or the one worth following!)</p>
""", unsafe_allow_html=True)

st.title("🐏 Sheepish Mentality 🐑🧠🤣🌾 - Multiplayer Game")
st.subheader("Play together in real time with your friends!")

if st.button("Summon Sheep"):
    st.image(
        "https://media.giphy.com/media/3ohhwehR8oQSD0W9Fu/giphy.gif",
        caption="A wild sheep appears! Open the sidebar and press \"Play\" if you want to play the game"
    )

if st.button("Sheepify the Stream"):
    st.markdown("""
        "🐑🐑🐑 Baa baa black sheep... 🐑🐑🐑",
                Open the sidebar and press \"Play\" if you want to play the game" \
                                            "
                                            """)


