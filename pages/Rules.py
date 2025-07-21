## Rules of the game
import streamlit as st

st.set_page_config(page_title="Game Rules", layout="centered")

st.title("📜 Game Rules")

st.markdown("""
### How to Play:
1. **Join or create a room** using a fun code.
2. **Submit your name** and select if you're the host.
3. The host clicks "Generate Question".
4. Players answer either:
   - open-ended prompts
   - pick one of the other players
   - multiple-choice questions
5. The host clicks "Reveal Herd Answer".
6. 🎯 If you're in the biggest group of matching answers, you earn a point.
7. 🐑 Tie? Nobody wins. Too many leaders, not enough sheep!

Use the sidebar to go back and start playing!
""")

st.page_link("Home.py", label="🏠 Back to Home", icon="🏠")
st.page_link("Play.py", label="🎮 Go to Game", icon="🎮")
