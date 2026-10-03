import streamlit as st
import pandas as pd
import yfinance as yf
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

st.markdown('<div class="main-title">TIS晨報 - 重要市場收盤表現</div>', unsafe_allow_html=True)

# 側邊欄：API 設定與日期選擇器
st.sidebar.header("⚙️ 系統設定與日期篩選")

# 日期選擇器：預設為今天，可讓使用者自由挑選歷史任一天的價格
selected_date = st.sidebar.date_input("選擇檢視日期", datetime.now().date())

default_api_key = ""
try:
    if "DASHSCOPE_API_KEY" in st.secrets:
        default_api_key = st.secrets["DASHSCOPE_API_KEY"]
except Exception:
    pass

api_key = st.sidebar.text_input(
    "阿里雲 / 中轉站 API Key", 
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

# 標的清單定義（使用更穩定的 Yahoo 代號）
group1_indices = {
    "道瓊工業指數": "^DJI",
    "那斯達克指數": "^IXIC",
    "標普500指數": "^GSPC",
    "費城半導體指數": "^SOX",
    "羅素2000指數": "^RUT",
    "英國FTSE 100": "^FTSE",
    "德國DAX指數": "^GDAXI",
    "法國CAC指數": "^FCHI",
    "道瓊歐洲600指數": "^STOXX"
}

group2_indices = {
    "日經225指數": "^N225",
    "南韓KOSPI指數": "^KS11",
    "恆生指數": "^HSI",
    "上證指數": "000001.SS",
    "新加坡STI指數": "^STI",
    "泰國曼谷SET指數": "^SET.BK",
    "富時馬來西亞指數": "^KLSE",
    "菲律賓綜合指數": "PCOMP.PS",
    "印尼雅加達指數": "^JKSE"
}

group3_indices = {
    "加權指數": "^TWII",
    "不含電子指數": "^TWII", # 備用防空值
    "上櫃指數": "^TWOII",
    "0050": "0050.TW",
    "0051": "0051.TW",
    "MSCI全球指數": "URTH",
    "歐洲Stoxx 50": "^STOXX50E",
    "MSCI新興市場": "EEM",
    "MSCI拉丁美洲": "ILF"
}

comm1 = {
    "Crude Oil 原油": "CL=F",
    "Natural Gas 天然氣": "NG=F",
    "Gold 黃金": "GC=F",
    "Silver 白銀": "SI=F",
    "Copper 銅": "HG=F"
}

comm2 = {
    "CRB 商品指數": "DBC", # 用具代表性的商品ETF替代以確保數據穩定
    "Corn 玉米": "ZC=F",
    "Wheat 小麥": "ZW=F",
    "Soybean 黃豆": "ZS=F",
    "Cotton 棉花": "CT=F"
}

comm3 = {
    "DXY 美元指數": "DX-Y.NYB",
    "BDI運價指數": "BDRY", # 替代為穩定的航運ETF
    "VIX 指數": "^VIX",
    "VXN 指數": "^VXN",
    "美國10年公債殖利率": "^TNX"
}

@st.cache_data(ttl=3600)
def fetch_market_data_by_date(tickers_dict, target_date):
    data = []
    # 為了確保選定日期前後有資料可抓（避開週末與假日），往前多抓 7 天
    start_dt = pd.to_datetime(target_date) - timedelta(days=10)
    end_dt = pd.to_datetime(target_date) + timedelta(days=1)
    
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'))
            
            if not hist.empty:
                # 過濾小於等於目標日期的資料
                hist = hist[hist.index.date <= target_date]
                if len(hist) >= 2:
                    close = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = close - prev
                    pct_change = (change / prev) * 100
                elif len(hist) == 1:
                    close = hist['Close'].iloc[-1]
                    change = 0.0
                    pct_change = 0.0
                else:
                    data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
                    continue
                
                data.append({
                    "指數/商品": name,
                    "收盤價": f"{close:,.2f}",
                    "變動": f"{change:+,.2f}",
                    "(%)": f"{pct_change:+.2f}%"
                })
            else:
                data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
        except Exception:
            data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
    return pd.DataFrame(data)

# 顯示市場收盤表格
st.markdown(f'<div class="section-header">全球主要股市收盤表現（基準日：{selected_date}）</div>', unsafe_allow_html=True)
col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    st.markdown("**美、歐股市**")
    st.dataframe(fetch_market_data_by_date(group1_indices, selected_date), use_container_width=True, hide_index=True)

with col_i2:
    st.markdown("**亞洲股市**")
    st.dataframe(fetch_market_data_by_date(group2_indices, selected_date), use_container_width=True, hide_index=True)

with col_i3:
    st.markdown("**台灣與國際指數**")
    st.dataframe(fetch_market_data_by_date(group3_indices, selected_date), use_container_width=True, hide_index=True)

st.markdown('<div class="section-header">大宗商品、匯率與債市表現</div>', unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.markdown("**金屬能源 (Commodity)**")
    st.dataframe(fetch_market_data_by_date(comm1, selected_date), use_container_width=True, hide_index=True)

with col_c2:
    st.markdown("**農作商品 (Commodity)**")
    st.dataframe(fetch_market_data_by_date(comm2, selected_date), use_container_width=True, hide_index=True)

with col_c3:
    st.markdown("**其他商品與指標**")
    st.dataframe(fetch_market_data_by_date(comm3, selected_date), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown('<div class="main-title">TIS晨報 - 新聞摘要 (基於路透、Yahoo財經、TradingView與 Qwen AI)</div>', unsafe_allow_html=True)

# API 呼叫函數
def call_qwen_api(messages_list, key, b_url, chosen_model):
    if not key:
        return None, "尚未偵測到 API Key。"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key.strip(), base_url=b_url.strip())
        models_to_try = [chosen_model, 'qwen-max', 'qwen-plus', 'qwen-turbo']
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_error = ""
        for m_name in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=m_name, messages=messages_list, temperature=0.3, response_format={"type": "json_object"}
                )
                if response and response.choices:
                    return response.choices[0].message.content, None
            except Exception as ex:
                last_error = str(ex)
                time.sleep(1.0)
        return None, f"所有模型嘗試皆失敗: {last_error}"
    except Exception as e:
        return None, f"API 初始化錯誤: {str(e)}"

def generate_ai_news_summary(api_key, b_url, model):
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
