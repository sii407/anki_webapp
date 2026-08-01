import streamlit as st
import pandas as pd
import random
from datetime import date

st.set_page_config(page_title="単語カードアプリ", page_icon="🎴", layout="centered")
st.title("🎴 単語カードアプリ")

# --------------------------------------------------
# 1. デッキ（CSV）の管理
# --------------------------------------------------
st.sidebar.header("📁 デッキ管理")

uploaded_files = st.sidebar.file_uploader(
    "CSVファイルをアップロード（複数可）",
    type=["csv"],
    accept_multiple_files=True
)

default_decks = {
    "サンプル英単語": pd.DataFrame({
        "word": ["apple", "banana", "challenge", "develop", "effort"],
        "meaning": ["りんご", "バナナ", "挑戦", "開発する", "努力"]
    })
}

decks = {}
if uploaded_files:
  for file in uploaded_files:
    try:
      df = pd.read_csv(file)
      if "word" in df.columns and "meaning" in df.columns:
        deck_name = file.name.rsplit('.', 1)[0]
        decks[deck_name] = df
      else:
        st.sidebar.error(f"⚠️ {file.name}: 'word' と 'meaning' 列が必要です。")
    except Exception as e:
      st.sidebar.error(f"⚠️ {file.name} 読み込み失敗: {e}")

if not decks:
  decks = default_decks

selected_deck_name = st.sidebar.selectbox("📚 学習するデッキを選択", list(decks.keys()))
current_df = decks[selected_deck_name]

# --------------------------------------------------
# 2. セッション状態（ランク・最終ランクアップ日）の初期化
# --------------------------------------------------
today_str = str(date.today())

# デッキ切り替え時の初期化
if "current_deck_name" not in st.session_state or st.session_state.current_deck_name != selected_deck_name:
  st.session_state.current_deck_name = selected_deck_name
  # 各単語のランク（初期値 1）
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
  # 最後にランクアップした日付（初期値 None）
  st.session_state.last_up_dates = {i: None for i in range(len(current_df))}
  st.session_state.current_word_idx = None
  st.session_state.show_meaning = False

# --------------------------------------------------
# 3. 出題可能単語のフィルタリングロジック
# --------------------------------------------------
def is_playable(idx):
  """今日学習（出題）できる単語かどうかを判定"""
  rank = st.session_state.word_ranks[idx]
  last_date = st.session_state.last_up_dates[idx]

  # すでに MAX (Rank 10) の場合は除外
  if rank >= 10:
    return False

  # Rank 7 以上かつ、今日すでにランクアップしている場合は本日制限（非表示）
  if rank >= 7 and last_date == today_str:
    return False

  return True

# 本日プレイ可能な単語のインデックス一覧
playable_indices = [i for i in range(len(current_df)) if is_playable(i)]

def pick_next_word():
  """次の出題単語をランダム選出"""
  valid_indices = [i for i in range(len(current_df)) if is_playable(i)]
  if not valid_indices:
    st.session_state.current_word_idx = None
  else:
    curr = st.session_state.current_word_idx
    if len(valid_indices) > 1 and curr in valid_indices:
      candidates = [i for i in valid_indices if i != curr]
      st.session_state.current_word_idx = random.choice(candidates)
    else:
      st.session_state.current_word_idx = random.choice(valid_indices)
  st.session_state.show_meaning = False

# 初期選択
if st.session_state.current_word_idx is None or st.session_state.current_word_idx not in playable_indices:
  pick_next_word()

# --------------------------------------------------
# 4. 全体進捗の表示
# --------------------------------------------------
total_count = len(current_df)
mastered_count = sum(1 for r in st.session_state.word_ranks.values() if r == 10)
progress_percentage = (mastered_count / total_count) if total_count > 0 else 0

st.write(f"### 📚 デッキ: **{selected_deck_name}**")
st.progress(progress_percentage)
st.caption(f"完全マスター (Rank 10): **{mastered_count} / {total_count} 単語**")

# --------------------------------------------------
# 5. メイン画面（判定分岐）
# --------------------------------------------------
# ケース1: デッキ内のすべての単語が Rank 10 になった場合
if mastered_count == total_count:
  st.balloons()
  st.success("🎉 おめでとうございます！すべての単語が MAX (Rank 10) に達しました！")
  st.info("このデッキは完全にマスターされました！")

# ケース2: すべてが Rank 10 ではないが、今日の制限で出題できる単語がない場合
elif len(playable_indices) == 0:
  st.info("🌙 **本日の学習は完了しました！**")
  st.write("Rank 7以上の単語は、記憶の定着のため1日1回しかランクアップできません。")
  st.write("明日になると再び復習できるようになります。お疲れ様でした！")

# ケース3: 通常の単語カード画面
else:
  curr_idx = st.session_state.current_word_idx
  curr_rank = st.session_state.word_ranks[curr_idx]

  current_word = current_df.iloc[curr_idx]["word"]
  current_meaning = current_df.iloc[curr_idx]["meaning"]

  # 制限に関する注記メッセージ
  limit_notice = ""
  if curr_rank >= 6:
    limit_notice = " *(正解するとRank 7以上になり、本日の出題は終了します)*"

  with st.container(border=True):
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
      st.caption("【表面】単語")
    with col_t2:
      st.markdown(f"**現在の評価:** `Rank {curr_rank} / 10`")

    st.markdown(f"# {current_word}")

    st.divider()

    st.caption("【裏面】意味")
    if st.session_state.show_meaning:
      st.markdown(f"### {current_meaning}")
    else:
      st.markdown("*？？？？（「意味を見る」ボタンを押してください）*")

  # 操作ボタン
  col1, col2 = st.columns(2)
  with col1:
    if st.button("👀 意味を見る / 隠す", use_container_width=True):
      st.session_state.show_meaning = not st.session_state.show_meaning
      st.rerun()

  with col2:
    if st.button("➡️ 評価せず別の単語へ", use_container_width=True):
      pick_next_word()
      st.rerun()

  st.write("---")
  st.write(f"**判定してランクを変更:** {limit_notice}")
  btn_col1, btn_col2 = st.columns(2)

  with btn_col1:
    if st.button("⭕ 正解！ ( Rank +1 )", type="primary", use_container_width=True):
      # ランクアップ処理
      new_rank = min(10, curr_rank + 1)
      st.session_state.word_ranks[curr_idx] = new_rank

      # Rank 7 以上へ上がった（または保持した）場合、本日の日付を記録
      if new_rank >= 7:
        st.session_state.last_up_dates[curr_idx] = today_str

      pick_next_word()
      st.rerun()

  with btn_col2:
    if st.button("❌ 不正解... ( Rank -1 )", use_container_width=True):
      # ランクダウン処理（最低 1）
      st.session_state.word_ranks[curr_idx] = max(1, curr_rank - 1)
      pick_next_word()
      st.rerun()

# --------------------------------------------------
# 6. サイドバーのリセットオプション
# --------------------------------------------------
st.sidebar.divider()
if st.sidebar.button("🔄 このデッキの進行状況をリセット"):
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
  st.session_state.last_up_dates = {i: None for i in range(len(current_df))}
  pick_next_word()
  st.rerun()
