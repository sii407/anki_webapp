import streamlit as st
import pandas as pd
import random
from datetime import date

st.set_page_config(page_title="単語カードアプリ", page_icon="🎴", layout="centered")
st.title("🎴 単語カードアプリ")

# --------------------------------------------------
# 1. デッキ（CSV）の管理（列位置による自動判別）
# --------------------------------------------------
st.sidebar.header("📁 デッキ管理")

uploaded_files = st.sidebar.file_uploader(
    "CSVファイルをアップロード（複数可）",
    type=["csv"],
    accept_multiple_files=True
)

# デフォルト（サンプル）デッキの準備（列名ではなく0, 1の列インデックスで管理）
default_data = pd.DataFrame([
    ["apple", "りんご"],
    ["banana", "バナナ"],
    ["challenge", "挑戦"],
    ["develop", "開発する"],
    ["effort", "努力"]
])

default_decks = {
    "サンプル英単語": default_data
}

decks = {}
if uploaded_files:
  for file in uploaded_files:
    try:
      # header=None で読み込み、1列目(0)と2列目(1)を自動認識
      df = pd.read_csv(file, header=None)

      # 最低2列以上あるかチェック
      if df.shape[1] >= 2:
        # 1行目が「word」「単語」などのヘッダーっぽい場合は自動除去
        first_row_str = str(df.iloc[0, 0]).lower()
        if first_row_str in ["word", "単語", "問題", "question", "front"]:
          df = df.iloc[1:].reset_index(drop=True)

        deck_name = file.name.rsplit('.', 1)[0]
        decks[deck_name] = df
      else:
        st.sidebar.error(f"⚠️ {file.name}: 2列以上のデータが必要です。")
    except Exception as e:
      st.sidebar.error(f"⚠️ {file.name} 読み込み失敗: {e}")

if not decks:
  decks = default_decks

selected_deck_name = st.sidebar.selectbox("📚 学習するデッキを選択", list(decks.keys()))
current_df = decks[selected_deck_name]

# --------------------------------------------------
# 2. セッション状態（ステート）の初期化・安全化処理
# --------------------------------------------------
today_str = str(date.today())

# デッキ切り替え時の初期化
if "current_deck_name" not in st.session_state or st.session_state.current_deck_name != selected_deck_name:
  st.session_state.current_deck_name = selected_deck_name
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
  st.session_state.last_up_dates = {i: None for i in range(len(current_df))}
  st.session_state.current_word_idx = None
  st.session_state.show_meaning = False

# 安全保護
if "word_ranks" not in st.session_state:
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
if "last_up_dates" not in st.session_state:
  st.session_state.last_up_dates = {i: None for i in range(len(current_df))}
if "show_meaning" not in st.session_state:
  st.session_state.show_meaning = False

# --------------------------------------------------
# 3. 出題可能単語のフィルタリングロジック
# --------------------------------------------------
def is_playable(idx):
  """今日学習（出題）できる単語かどうかを判定"""
  if idx not in st.session_state.word_ranks:
    return False

  rank = st.session_state.word_ranks.get(idx, 1)
  last_date = st.session_state.last_up_dates.get(idx, None)

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
    curr = st.session_state.get("current_word_idx", None)
    if len(valid_indices) > 1 and curr in valid_indices:
      candidates = [i for i in valid_indices if i != curr]
      st.session_state.current_word_idx = random.choice(candidates)
    else:
      st.session_state.current_word_idx = random.choice(valid_indices)
  st.session_state.show_meaning = False

# 初期選択
if st.session_state.get("current_word_idx") is None or st.session_state.current_word_idx not in playable_indices:
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
if mastered_count == total_count:
  st.balloons()
  st.success("🎉 おめでとうございます！すべての単語が MAX (Rank 10) に達しました！")
  st.info("このデッキは完全にマスターされました！")

elif len(playable_indices) == 0:
  st.info("🌙 **本日の学習は完了しました！**")
  st.write("Rank 7以上の単語は、記憶の定着のため1日1回しかランクアップできません。")
  st.write("明日になると再び復習できるようになります。お疲れ様でした！")

else:
  curr_idx = st.session_state.current_word_idx
  curr_rank = st.session_state.word_ranks[curr_idx]

  # 【自動判定】1列目(0)を問題、2列目(1)を答えとして取得
  current_word = current_df.iloc[curr_idx, 0]
  current_meaning = current_df.iloc[curr_idx, 1]

  # 制限注記
  limit_notice = ""
  if curr_rank >= 6:
    limit_notice = " *(正解するとRank 7以上になり、本日の出題は終了します)*"

  with st.container(border=True):
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
      st.caption("【1列目】問題")
    with col_t2:
      st.markdown(f"**現在の評価:** `Rank {curr_rank} / 10`")

    st.markdown(f"# {current_word}")

    st.divider()

    st.caption("【2列目】答え")
    if st.session_state.show_meaning:
      st.markdown(f"### {current_meaning}")
    else:
      st.markdown("*？？？？（「答えを見る」ボタンを押してください）*")

  # 操作ボタン
  col1, col2 = st.columns(2)
  with col1:
    if st.button("👀 答えを見る / 隠す", use_container_width=True):
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
      new_rank = min(10, curr_rank + 1)
      st.session_state.word_ranks[curr_idx] = new_rank

      if new_rank >= 7:
        st.session_state.last_up_dates[curr_idx] = today_str

      pick_next_word()
      st.rerun()

  with btn_col2:
    if st.button("❌ 不正解... ( Rank -1 )", use_container_width=True):
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
