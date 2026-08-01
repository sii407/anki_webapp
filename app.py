import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="単語カードアプリ", page_icon="🎴")
st.title("🎴 CSV対応 単語カードアプリ")

# --------------------------------------------------
# 1. CSVファイルのアップロード機能
# --------------------------------------------------
uploaded_file = st.sidebar.file_uploader(
    "CSVファイルをアップロード（列名: word, meaning）", type=["csv"])

# 状態管理（セッション状態の初期化）
if "word_index" not in st.state_state if "word_index" not in st.session_state:
  st.session_state.word_index = 0
if "show_meaning" not in st.session_state:
  st.session_state.show_meaning = False

# デフォルトデータ（CSVが読み込まれていない場合の表示用）
default_data = pd.DataFrame({
    "word": ["apple", "banana", "challenge"],
    "meaning": ["りんご", "バナナ", "挑戦"]
})

if uploaded_file is not None:
  try:
    df = pd.read_csv(uploaded_file)
    # 必要な列が存在するかチェック
    if "word" not in df.columns or "meaning" not in df.columns:
      st.error("CSVファイルには 'word' と 'meaning' の列が必要です。")
      df = default_data
  except Exception as e:
    st.error(f"ファイル読み込みエラー: {e}")
    df = default_data
else:
  st.info("👈 サイドバーからCSVをアップロードできます（現在はサンプルデータを使用中）。")
  df = default_data

# --------------------------------------------------
# 2. 単語カードの表示コントロール
# --------------------------------------------------
total_words = len(df)
current_idx = st.session_state.word_index % total_words
current_word = df.iloc[current_idx]["word"]
current_meaning = df.iloc[current_idx]["meaning"]

st.write(f"**進捗:** {current_idx + 1} / {total_words}")

# カード表示エリア
with st.container(border=True):
  st.subheader("【表面】単語")
  st.markdown(f"# {current_word}")

  st.divider()

  st.subheader("【裏面】意味")
  if st.session_state.show_meaning:
    st.markdown(f"### {current_meaning}")
  else:
    st.markdown("*？？？？（ボタンを押して確認）*")

# --------------------------------------------------
# 3. 操作ボタン
# --------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
  if st.button("👀 意味を見る / 隠す", use_container_width=True):
    st.session_state.show_meaning = not st.session_state.show_meaning
    st.rerun()

with col2:
  if st.button("➡️ 次の単語", use_container_width=True):
    st.session_state.word_index += 1
    st.session_state.show_meaning = False
    st.rerun()

with col3:
  if st.button("🔀 ランダム", use_container_width=True):
    st.session_state.word_index = random.randint(0, total_words - 1)
    st.session_state.show_meaning = False
    st.rerun()
