import streamlit as st
import pandas as pd
import random

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
# 2. セッション状態（単語ごとのランク管理）の初期化
# --------------------------------------------------
# デッキ変更時の初期化
if "current_deck_name" not in st.session_state or st.session_state.current_deck_name != selected_deck_name:
  st.session_state.current_deck_name = selected_deck_name
  # 各単語の初期ランクを 1 に設定
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
  st.session_state.current_word_idx = None
  st.session_state.show_meaning = False

# まだ Rank 10 になっていない単語のインデックスを取得
unmastered_indices = [idx for idx,
                      rank in st.session_state.word_ranks.items() if rank < 10]

# 次の出題単語を選ぶ関数
def pick_next_word():
  remaining = [idx for idx,
               rank in st.session_state.word_ranks.items() if rank < 10]
  if not remaining:
    st.session_state.current_word_idx = None
  else:
    # 直前と同じ単語が連続しないように配慮（残りが1つの場合を除く）
    curr = st.session_state.current_word_idx
    if len(remaining) > 1 and curr in remaining:
      candidates = [i for i in remaining if i != curr]
      st.session_state.current_word_idx = random.choice(candidates)
    else:
      st.session_state.current_word_idx = random.choice(remaining)
  st.session_state.show_meaning = False

# 初期選択
if st.session_state.current_word_idx is None and unmastered_indices:
  pick_next_word()

# --------------------------------------------------
# 3. 進捗・全般ステータス表示
# --------------------------------------------------
total_count = len(current_df)
mastered_count = total_count - len(unmastered_indices)
progress_percentage = (mastered_count / total_count) if total_count > 0 else 0

st.write(f"### 📚 デッキ: **{selected_deck_name}**")
st.progress(progress_percentage)
st.caption(f"完全マスター (Rank 10): **{mastered_count} / {total_count} 単語**")

# --------------------------------------------------
# 4. メイン画面（クリア判定 判定分岐）
# --------------------------------------------------
if len(unmastered_indices) == 0:
  # 🎉 全単語 Rank 10 達成時の表示
  st.balloons()
  st.success("🎉 おめでとうございます！すべての単語が MAX (Rank 10) に達しました！")
  st.info("このデッキは完全にマスターされました！他のデッキを選択するか、リセットして再度挑戦できます。")

  if st.button("🔄 このデッキのランクをリセットして最初から解く"):
    st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
    pick_next_word()
    st.rerun()

else:
  # 通常の単語カード学習画面
  curr_idx = st.session_state.current_word_idx
  curr_rank = st.session_state.word_ranks[curr_idx]

  current_word = current_df.iloc[curr_idx]["word"]
  current_meaning = current_df.iloc[curr_idx]["meaning"]

  # ランクに応じたバッジ表示
  rank_stars = "⭐" if curr_rank == 10 else f"Rank {curr_rank} / 10"

  with st.container(border=True):
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
      st.caption("【表面】単語")
    with col_t2:
      st.markdown(f"**現在の評価:** `{rank_stars}`")

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
  st.write("**判定してランクを変更:**")
  btn_col1, btn_col2 = st.columns(2)

  with btn_col1:
    if st.button("⭕ 正解！ ( Rank +1 )", type="primary", use_container_width=True):
      # ランクを 1 上げる（最大 10）
      st.session_state.word_ranks[curr_idx] = min(
          10, st.session_state.word_ranks[curr_idx] + 1)
      pick_next_word()
      st.rerun()

  with btn_col2:
    if st.button("❌ 不正解... ( Rank -1 )", use_container_width=True):
      # ランクを 1 下げる（最低 1）
      st.session_state.word_ranks[curr_idx] = max(
          1, st.session_state.word_ranks[curr_idx] - 1)
      pick_next_word()
      st.rerun()

# --------------------------------------------------
# 5. サイドバーの設定・ランク一覧確認
# --------------------------------------------------
st.sidebar.divider()
st.sidebar.subheader("📊 現在の単語別ランク一覧")

# 現在のデッキの単語ごとのランクをテーブル表示
rank_data = []
for i, row in current_df.iterrows():
  rank_data.append({
      "単語": row["word"],
      "ランク": f"Rank {st.session_state.word_ranks[i]}" if st.session_state.word_ranks[i] < 10 else "MAX ⭐"
  })

st.sidebar.dataframe(pd.DataFrame(rank_data),
                     hide_index=True, use_container_width=True)

if st.sidebar.button("🔄 このデッキの進行状況を全リセット"):
  st.session_state.word_ranks = {i: 1 for i in range(len(current_df))}
  pick_next_word()
  st.rerun()
