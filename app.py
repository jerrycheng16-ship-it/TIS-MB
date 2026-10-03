import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import json
import time

# 頁面設定
st.set_page_config(
    page_title="TIS晨報 - 市場收盤與新聞摘要",
    page_icon="📈",
    layout="wide"
)

# 自訂 CSS 樣式
st.markdown("""
    <style>
    .main-title {
        font-size: 24px;
        font-weight: bold;
        color: #ffffff;
        background-color: #0d1b2a;
        padding: 10px 15px;
        border-radius: 5px;
        margin-bottom: 15px;
    }
    .section-header {
        font-size: 16px;
        font-weight: bold;
        color: #ffffff;
        background-color: #1b263b;
        padding: 8px 12px;
        border-radius: 4px;
        margin-top: 10px;
        margin-bottom: 8px;
    }
    .news-card {
        background-color: #1e222d;
        border-left: 4px solid #2962ff;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 4px;
        color: #d1d4dc;
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">TIS晨報 - 重要市場收盤表現 (Alpha Vantage 驅動)</div>', unsafe_allow_html=True)

# 側邊欄：系統設定與 API Key
st.sidebar.header("⚙️ 系統設定與 API 連結")
selected_date = st.sidebar.date_input("選擇檢視收盤日期", datetime.now().date())

# Alpha Vantage API Key 設定
default_av_key = ""
try:
    if "ALPHA_VANTAGE_API_KEY" in st.secrets:
        default_av_key = st.secrets["ALPHA_VANTAGE_API_KEY"]
except Exception:
    pass

av_api_key = st.sidebar.text_input(
    "Alpha Vantage API Key", 
    type="password", 
    value=default_av_key
)

# Qwen / 阿里雲 API 設定（給新聞摘要用）
default_api_key = ""
try:
    if "DASHSCOPE_API_KEY" in st.secrets:
        default_api_key = st.secrets["DASHSCOPE_API_KEY"]
except Exception:
    pass

api_key = st.sidebar.text_input(
    "阿里雲 / 中轉站 API Key (新聞摘要)", 
    type="password", 
    value=default_api_key
)

default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
try:
    if "DASHSCOPE_BASE_URL" in st.secrets:
        default_base_url = st.secrets["DASHSCOPE_BASE_URL"]
except Exception:
    pass

base_url_input = st.sidebar.text_input("API Base URL", value=default_base_url)
model_choice = st.sidebar.selectbox("選擇大模型", ["qwen-max", "qwen-plus", "qwen-turbo"])

# 定義標的清單（對應 Alpha Vantage 支援的代號格式）
group1_indices = {
    "道瓊工業指數": "DIA", "那斯達克指數": "QQQ", "標普500指數": "SPY",
    "費城半導體指數": "SOXX", "羅素2000指數": "IWM", "英國FTSE 100": "ISF.L",
    "德國DAX指數": "DAX.EX", "法國CAC指數": "CAC.PA", "道瓊歐洲600指數": "EXV1.DE"
}

group2_indices = {
    "日經225指數": "1321.T", "南韓KOSPI指數": "069500.KS", "恆生指數": "2800.HK",
    "上證指數": "510050.SS", "新加坡STI指數": "ES3.SI", "泰國曼谷SET指數": "SET50.BK",
    "富時馬來西亞指數": "0820EA.KL", "菲律賓綜合指數": "PMP.PS", "印尼雅加達指數": "XIIC.JK"
}

group3_indices = {
    "加權指數": "^TWII", "不含電子指數": "^TWII", "上櫃指數": "TWOII.TW",
    "0050": "0050.TW", "0051": "0051.TW", "MSCI全球指數": "URTH",
    "歐洲Stoxx 50": "FEZ", "MSCI新興市場": "EEM", "MSCI拉丁美洲": "ILF"
}

comm1 = {
    "Crude Oil 原油": "USO", "Natural Gas 天然氣": "UNG", "Gold 黃金": "GLD",
    "Silver 白銀": "SLV", "Copper 銅": "CPER"
}

comm2 = {
    "CRB 商品指數": "DBC", "Corn 玉米": "CORN", "Wheat 小麥": "WEAT",
    "Soybean 黃豆": "SOYB", "Cotton 棉花": "BAL"
}

comm3 = {
    "DXY 美元指數": "UUP", "BDI運價指數": "BDRY", "VIX 指數": "VIXY",
    "VXN 指數": "VIXY", "美國10年公債殖利率": "IEF"
}

# 透過 Alpha Vantage 抓取歷史與收盤資料的函數
@st.cache_data(ttl=3600)
def fetch_alpha_vantage_data(tickers_dict, target_date_str, av_key):
    data = []
    target_dt = pd.to_datetime(target_date_str)
    
    for name, symbol in tickers_dict.items():
        val_close, val_change, val_pct = "N/A", "N/A", "N/A"
        if not av_key:
            data.append({"指數/商品": name, "收盤價": "未填 API Key", "變動": "N/A", "(%)": "N/A"})
            continue
            
        try:
            # 呼叫 Alpha Vantage DAILY 接口
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={av_key}"
            response = requests.get(url)
            result = response.json()
            
            time.sleep(0.2) # 避免超過頻率限制
            
            time_series = result.get("Time Series (Daily)")
            if time_series:
                df = pd.DataFrame.from_dict(time_series, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                
                # 篩選小於等於目標日期的資料
                df = df[df.index <= target_dt]
                if not df.empty:
                    close = float(df['4. close'].iloc[-1])
                    prev = float(df['4. close'].iloc[-2]) if len(df) >= 2 else close
                    change = close - prev
                    pct_change = (change / prev) * 100 if prev != 0 else 0.0
                    
                    val_close = f"{close:,.2f}"
                    val_change = f"{change:+,.2f}"
                    val_pct = f"{pct_change:+.2f}%"
        except Exception:
            pass
            
        data.append({
            "指數/商品": name,
            "收盤價": val_close,
            "變動": val_change,
            "(%)": val_pct
        })
    return pd.DataFrame(data)

st.markdown(f'<div class="section-header">全球主要股市與商品收盤表現（基準日：{selected_date}）- Alpha Vantage 數據源</div>', unsafe_allow_html=True)
col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    st.markdown("**美、歐股市**")
    df1 = fetch_alpha_vantage_data(group1_indices, str(selected_date), av_api_key)
    edited_df1 = st.data_editor(df1, hide_index=True, key="edit_g1")

with col_i2:
    st.markdown("**亞洲股市**")
    df2 = fetch_alpha_vantage_data(group2_indices, str(selected_date), av_api_key)
    edited_df2 = st.data_editor(df2, hide_index=True, key="edit_g2")

with col_i3:
    st.markdown("**台灣與國際指數**")
    df3 = fetch_alpha_vantage_data(group3_indices, str(selected_date), av_api_key)
    edited_df3 = st.data_editor(df3, hide_index=True, key="edit_g3")

st.markdown('<div class="section-header">大宗商品、匯率與債市表現</div>', unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.markdown("**金屬能源 (Commodity)**")
    df_c1 = fetch_alpha_vantage_data(comm1, str(selected_date), av_api_key)
    edited_df_c1 = st.data_editor(df_c1, hide_index=True, key="edit_c1")

with col_c2:
    st.markdown("**農作商品 (Commodity)**")
    df_c2 = fetch_alpha_vantage_data(comm2, str(selected_date), av_api_key)
    edited_df_c2 = st.data_editor(df_c2, hide_index=True, key="edit_c2")

with col_c3:
    st.markdown("**其他商品與指標**")
    df_c3 = fetch_alpha_vantage_data(comm3, str(selected_date), av_api_key)
    edited_df_c3 = st.data_editor(df_c3, hide_index=True, key="edit_c3")

# =========================================================
# 🔍 除錯專用表格：櫃買指數、0050、0051 近 10 天歷史收盤價
# =========================================================
st.markdown("---")
st.markdown('<div class="section-header">🔍 除錯專用：櫃買指數、0050、0051 近 10 天歷史收盤價檢視 (Alpha Vantage)</div>', unsafe_allow_html=True)

debug_tickers = {
    "0050 (0050.TW)": "0050.TW",
    "0051 (0051.TW)": "0051.TW",
    "櫃買指數 (TWOII)": "TWOII.TW"
}

all_debug_data = {}
for label, symbol in debug_tickers.items():
    try:
        if av_api_key:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={av_api_key}"
            res = requests.get(url).json()
            time.sleep(0.2)
            ts = res.get("Time Series (Daily)")
            if ts:
                df_sub = pd.DataFrame.from_dict(ts, orient='index')
                df_sub.index = pd.to_datetime(df_sub.index).strftime('%Y-%m-%d')
                all_debug_data[label] = df_sub['4. close'].tail(10).astype(float)
                continue
        all_debug_data[label] = pd.Series(dtype=float)
    except Exception:
        all_debug_data[label] = pd.Series(dtype=float)

debug_combined_df = pd.DataFrame(all_debug_data)
if not debug_combined_df.empty:
    debug_combined_df = debug_combined_df.sort_index(ascending=False)
    st.dataframe(debug_combined_df, use_container_width=True)
else:
    st.warning("⚠️ 目前無法取得除錯標的的歷史資料。")

st.markdown("---")
st.markdown(f'<div class="main-title">TIS晨報 - 新聞摘要 ({selected_date})</div>', unsafe_allow_html=True)

def call_qwen_api(messages_list, key, b_url, chosen_model):
    if not key:
        return None, "尚未偵測到 API Key。"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key.strip(), base_url=b_url.strip())
        response = client.chat.completions.create(
            model=chosen_model, messages=messages_list, temperature=0.3, response_format={"type": "json_object"}
        )
        if response and response.choices:
            return response.choices[0].message.content, None
    except Exception as e:
        return None, str(e)
    return None, "未知錯誤"

def generate_ai_news_summary(api_key, b_url, model):
    if not api_key:
        return {"美股焦點": "⚠️ 尚未設定 API Key", "債市焦點": "---", "能源盤後": "---", "貴金屬盤後": "---", "紐約匯市": "---", "台幣焦點": "---"}
    prompt = f"""
    請模擬專業華爾街金融分析師，依據路透社(Reuters)、Yahoo Finance與TradingView的最新市場動態，產出日期為 {selected_date} 的專業「TIS晨報-新聞摘要」。
    請嚴格分成以下六大板塊，以專業流暢的繁體中文撰寫：
    1. 美股焦點
    2. 債市焦點
    3. 能源盤後
    4. 貴金屬盤後
    5. 紐約匯市
    6. 台幣焦點
    
    請務必以 JSON 格式回傳，鍵名必須對應為：us_stock, bond_market, energy, precious_metals, forex, twd。
    """
    messages = [{'role': 'system', 'content': '你是一個頂尖的財經主編。'}, {'role': 'user', 'content': prompt}]
    res_str, err = call_qwen_api(messages, api_key, b_url, model)
    if not res_str:
        return {"美股焦點": f"❌ 錯誤: {err}", "債市焦點": "---", "能源盤後": "---", "貴金屬盤後": "---", "紐約匯市": "---", "台幣焦點": "---"}
    try:
        content_dict = json.loads(res_str)
        return {
            "美股焦點": content_dict.get("us_stock", ""),
            "債市焦點": content_dict.get("bond_market", ""),
            "能源盤後": content_dict.get("energy", ""),
            "貴金屬盤後": content_dict.get("precious_metals", ""),
            "紐約匯市": content_dict.get("forex", ""),
            "台幣焦點": content_dict.get("twd", "")
        }
    except Exception as e:
        return {"美股焦點": f"❌ 解析失敗: {str(e)}", "債市焦點": "---", "能源盤後": "---", "貴金屬盤後": "---", "紐約匯市": "---", "台幣焦點": "---"}

if st.sidebar.button("🔄 立即更新新聞摘要") or 'news_cache' not in st.session_state:
    with st.spinner("正在生成摘要..."):
        st.session_state['news_cache'] = generate_ai_news_summary(api_key, base_url_input, model_choice)
        st.session_state['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

news_data = st.session_state.get('news_cache', {})
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section-header">美股焦點</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("美股焦點", "")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">能源盤後</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("能源盤後", "")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">紐約匯市</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("紐約匯市", "")}</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section-header">債市焦點</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("債市焦點", "")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">貴金屬盤後</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("貴金屬盤後", "")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">台幣焦點</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="news-card">{news_data.get("台幣焦點", "")}</div>', unsafe_allow_html=True)
