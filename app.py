import streamlit as st
import pandas as pd
import random
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="単語カードアプリ", page_icon="🎴", layout="centered")

# --------------------------------------------------
# 1. Supabase 接続初期化
# --------------------------------------------------
@st.cache_resource
def get_supabase_client() -> Client:
  try:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)
  except Exception as e:
    st.error(f"Supabaseの接続設定(Secrets)エラー: {e}")
    st.stop()

supabase = get_supabase_client()

# セッション状態の自動復元（リロード対策）
if "user" not in st.session_state or st.session_state.user is None:
  try:
    session = supabase.auth.get_session()
    if session and session.user:
      st.session_state.user = session.user
    else:
      st.session_state.user = None
  except Exception:
    st.session_state.user = None

# --------------------------------------------------
# 2. ユーザー認証機能 (ログイン / 新規登録)
# --------------------------------------------------
st.sidebar.header(" ユーザー認証")

if st.session_state.user is None:
  auth_mode = st.sidebar.radio("モード選択", ["ログイン", "新規アカウント登録"])
  email = st.sidebar.text_input("メールアドレス")
  password = st.sidebar.text_input("パスワード", type="password")

  if auth_mode == "新規アカウント登録":
    if st.sidebar.button("アカウント作成して開始", type="primary", use_container_width=True):
      if email and password:
        try:
          res = supabase.auth.sign_up(
              {"email": email, "password": password})
          login_res = supabase.auth.sign_in_with_password(
              {"email": email, "password": password})
          if login_res.user:
            st.session_state.user = login_res.user
            st.sidebar.success("アカウントを作成し、ログインしました！")
            st.rerun()
          elif res.user:
            st.session_state.user = res.user
            st.sidebar.success("アカウントを作成しました！")
            st.rerun()
        except Exception as e:
          try:
            login_res = supabase.auth.sign_in_with_password(
                {"email": email, "password": password})
            if login_res.user:
              st.session_state.user = login_res.user
              st.sidebar.success("ログインしました！")
              st.rerun()
          except Exception as le:
            st.sidebar.error(f"エラー: {e}")
      else:
        st.sidebar.warning("メールアドレスとパスワードを入力してください。")

  else:  # ログイン
    if st.sidebar.button("ログイン", type="primary", use_container_width=True):
      if email and password:
        try:
          res = supabase.auth.sign_in_with_password(
              {"email": email, "password": password})
          if res.user:
            st.session_state.user = res.user
            st.sidebar.success("ログインしました！")
            st.rerun()
        except Exception as e:
          st.sidebar.error(f"ログインエラー: {e}")
      else:
        st.sidebar.warning("メールアドレスとパスワードを入力してください。")

  st.info("アプリを利用するには、サイドバーから **ログイン** または **新規アカウント登録** を行ってください。")
  st.stop()

else:
  user_email = st.session_state.user.email
  user_id = st.session_state.user.id
  st.sidebar.write(f"ログイン中: **{user_email}**")
  if st.sidebar.button("ログアウト", use_container_width=True):
    try:
      supabase.auth.sign_out()
    except Exception:
      pass
    st.session_state.user = None
    st.session_state.current_word_id = None
    st.rerun()

st.sidebar.divider()

# --------------------------------------------------
# 3. データベース操作関数
# --------------------------------------------------
def save_csv_to_supabase(deck_name, df, current_user_id):
  try:
    supabase.table("words").delete().eq("user_id", current_user_id).eq(
        "deck_name", deck_name).execute()
    data_to_insert = []
    for _, row in df.iterrows():
      data_to_insert.append({
          "user_id": current_user_id,
          "deck_name": deck_name,
          "question": str(row[0]),
          "answer": str(row[1]),
          "rank": 1,
          "last_up_date": None
      })
    if data_to_insert:
      supabase.table("words").insert(data_to_insert).execute()
  except Exception as e:
    st.error(f"データ保存エラー: {e}")

def load_decks(current_user_id):
  try:
    res = supabase.table("words").select("deck_name").eq(
        "user_id", current_user_id).execute()
    if not res.data:
      return []
    decks = list(set([item["deck_name"]
                 for item in res.data if item.get("deck_name")]))
    decks.sort()
    return decks
  except Exception as e:
    st.error(f"デッキ取得エラー: {e}")
    return []

def load_words(deck_name, current_user_id):
  try:
    res = supabase.table("words").select(
        "*").eq("user_id", current_user_id).eq("deck_name", deck_name).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()
  except Exception as e:
    st.error(f"単語読み込みエラー: {e}")
    return pd.DataFrame()

def update_word_progress(word_id, new_rank, up_date=None):
  try:
    update_data = {"rank": new_rank}
    if up_date is not None:
      update_data["last_up_date"] = up_date
    supabase.table("words").update(update_data).eq("id", word_id).execute()
  except Exception as e:
    st.error(f"進捗更新エラー: {e}")

def reset_deck_progress(deck_name, current_user_id):
  try:
    supabase.table("words").update({"rank": 1, "last_up_date": None}).eq(
        "user_id", current_user_id).eq("deck_name", deck_name).execute()
  except Exception as e:
    st.error(f"リセットエラー: {e}")

# --------------------------------------------------
# 4. サイドバー・デッキ管理 & CSVアップロード
# --------------------------------------------------
st.sidebar.header("デッキ管理")

uploaded_files = st.sidebar.file_uploader(
    "CSVファイルをアップロード（複数可）",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
  for file in uploaded_files:
    try:
      df = pd.read_csv(file, header=None)
      if df.shape[1] >= 2:
        first_row_str = str(df.iloc[0, 0]).lower()
        if first_row_str in ["word", "単語", "問題", "question", "front"]:
          df = df.iloc[1:].reset_index(drop=True)

        deck_name = file.name.rsplit('.', 1)[0]
        save_csv_to_supabase(deck_name, df, user_id)
        st.sidebar.success(f" {file.name} を保存しました！")
      else:
        st.sidebar.error(f"{file.name}: 2列以上のデータが必要です。")
    except Exception as e:
      st.sidebar.error(f"{file.name} 保存失敗: {e}")

existing_decks = load_decks(user_id)

# 登録データがない場合の案内表示
if not existing_decks:
  st.info("単語データがありません。画面左のサイドバーから **CSVファイルをアップロード** してください。")
  st.stop()

selected_deck_name = st.sidebar.selectbox("学習するデッキを選択", existing_decks)
current_df = load_words(selected_deck_name, user_id)

# --------------------------------------------------
# 5. 出題ロジック
# --------------------------------------------------
today_str = str(date.today())

def is_playable(row):
  rank = row.get("rank", 1)
  last_date = row.get("last_up_date", None)
  if rank >= 10:
    return False
  if rank >= 7 and last_date == today_str:
    return False
  return True

playable_df = current_df[current_df.apply(
    is_playable, axis=1)] if not current_df.empty else pd.DataFrame()

if "current_word_id" not in st.session_state:
  st.session_state.current_word_id = None
if "show_meaning" not in st.session_state:
  st.session_state.show_meaning = False

def pick_next_word():
  p_df = current_df[current_df.apply(
      is_playable, axis=1)] if not current_df.empty else pd.DataFrame()
  if p_df.empty:
    st.session_state.current_word_id = None
  else:
    valid_ids = p_df["id"].tolist()
    curr_id = st.session_state.current_word_id
    if len(valid_ids) > 1 and curr_id in valid_ids:
      candidates = [wid for wid in valid_ids if wid != curr_id]
      st.session_state.current_word_id = random.choice(candidates)
    else:
      st.session_state.current_word_id = random.choice(valid_ids)
  st.session_state.show_meaning = False

if (st.session_state.current_word_id is None or
        (not playable_df.empty and st.session_state.current_word_id not in playable_df["id"].values)):
  pick_next_word()

# --------------------------------------------------
# 6. メイン画面表示
# --------------------------------------------------
total_count = len(current_df)
mastered_count = len(current_df[current_df["rank"] == 10]) if (
    not current_df.empty and "rank" in current_df.columns) else 0
progress_percentage = (mastered_count / total_count) if total_count > 0 else 0

st.write(f"### 📚 デッキ: **{selected_deck_name}**")
st.progress(progress_percentage)
st.caption(f"完全マスター (Rank 10): **{mastered_count} / {total_count} 単語**")

if mastered_count == total_count and total_count > 0:
  st.balloons()
  st.success("🎉 すべての単語が MAX (Rank 10) に達しました！")
  st.info("このデッキはマスターされました！")

elif playable_df.empty:
  st.info("**本日の学習は完了しました！**")
  st.write("Rank 7以上の単語は、記憶の定着のため1日1回しかランクアップできません。")
  st.write("明日になると再び復習できるようになります。お疲れ様でした！")

else:
  curr_row = current_df[current_df["id"] ==
                        st.session_state.current_word_id].iloc[0]
  curr_id = curr_row["id"]
  curr_word = curr_row["question"]
  curr_meaning = curr_row["answer"]
  curr_rank = curr_row["rank"]

  limit_notice = ""
  if curr_rank >= 6:
    limit_notice = " *(正解するとRank 7以上になり、本日の出題は終了します)*"

  with st.container(border=True):
    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
      st.caption("【1列目】問題")
    with col_t2:
      st.markdown(f"**現在の評価:** `Rank {curr_rank} / 10`")

    st.markdown(f"# {curr_word}")
    st.divider()
    st.caption("【2列目】答え")
    if st.session_state.show_meaning:
      st.markdown(f"### {curr_meaning}")
    else:
      st.markdown("*？？？？（「答えを見る」ボタンを押してください）*")

  def toggle_meaning():
    st.session_state.show_meaning = not st.session_state.show_meaning

  st.button("答えを見る", use_container_width=True, on_click=toggle_meaning)

  btn_col1, btn_col2 = st.columns(2)

  with btn_col1:
    if st.button("正解 ( Rank +1 )", type="primary", use_container_width=True):
      new_rank = min(10, curr_rank + 1)
      up_d = today_str if new_rank >= 7 else None
      update_word_progress(curr_id, new_rank, up_d)
      pick_next_word()
      st.rerun()

  with btn_col2:
    if st.button("不正解( Rank -1 )", use_container_width=True):
      new_rank = max(1, curr_rank - 1)
      update_word_progress(curr_id, new_rank)
      pick_next_word()
      st.rerun()

st.sidebar.divider()
if st.sidebar.button("このデッキの進行状況をリセット"):
  reset_deck_progress(selected_deck_name, user_id)
  pick_next_word()
  st.rerun()
