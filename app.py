import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import json

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

# 側邊欄：API 設定（優先從 st.secrets 讀取）
st.sidebar.header("⚙️ 系統設定")

default_api_key = ""
try:
    if "DASHSCOPE_API_KEY" in st.secrets:
        default_api_key = st.secrets["DASHSCOPE_API_KEY"]
except Exception:
    pass

api_key = st.sidebar.text_input(
    "阿里雲 API Key (DashScope)", 
    type="password", 
    value=default_api_key
)

model_choice = st.sidebar.selectbox("選擇阿里雲模型", ["qwen-max", "qwen-plus", "qwen-turbo"])

st.sidebar.markdown("---")
st.sidebar.markdown("### ⏰ 自動更新機制")
st.sidebar.write("系統設定於 **每天早上 07:00** 自動重新整理並呼叫 AI 生成最新晨報摘要。")

# 標的清單定義
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
    "泰國曼谷SET指數": "^SETI",
    "富時馬來西亞指數": "^KLSE",
    "菲律賓綜合指數": "PCOMP.PS",
    "印尼雅加達指數": "^JKSE"
}

group3_indices = {
    "加權指數": "^TWII",
    "不含電子指數": "^TWII",
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
    "CRB 商品指數": "^CRB",
    "Corn 玉米": "ZC=F",
    "Wheat 小麥": "ZW=F",
    "Soybean 黃豆": "ZS=F",
    "Cotton 棉花": "CT=F"
}

comm3 = {
    "DXY 美元指數": "DX-Y.NYB",
    "BDI運價指數": "BDI",
    "VIX 指數": "^VIX",
    "VXN 指數": "^VXN",
    "美國10年公債殖利率": "^TNX"
}

@st.cache_data(ttl=3600)
def fetch_market_data(tickers_dict):
    data = []
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = close - prev
                pct_change = (change / prev) * 100
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

# 市場表格呈現
st.markdown('<div class="section-header">全球主要股市收盤表現</div>', unsafe_allow_html=True)
col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    st.markdown("**美、歐股市**")
    st.dataframe(fetch_market_data(group1_indices), use_container_width=True, hide_index=True)

with col_i2:
    st.markdown("**亞洲股市**")
    st.dataframe(fetch_market_data(group2_indices), use_container_width=True, hide_index=True)

with col_i3:
    st.markdown("**台灣與國際指數**")
    st.dataframe(fetch_market_data(group3_indices), use_container_width=True, hide_index=True)

st.markdown('<div class="section-header">大宗商品、匯率與債市表現</div>', unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.markdown("**金屬能源 (Commodity)**")
    st.dataframe(fetch_market_data(comm1), use_container_width=True, hide_index=True)

with col_c2:
    st.markdown("**農作商品 (Commodity)**")
    st.dataframe(fetch_market_data(comm2), use_container_width=True, hide_index=True)

with col_c3:
    st.markdown("**其他商品與指標**")
    st.dataframe(fetch_market_data(comm3), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown('<div class="main-title">TIS晨報 - 新聞摘要 (基於路透、Yahoo財經、TradingView與阿里雲 Qwen AI)</div>', unsafe_allow_html=True)

# 透過阿里雲 DashScope API 生成新聞摘要
def generate_ai_news_summary(api_key, model):
    if not api_key:
        return {
            "美股焦點": "⚠️ 尚未偵測到 API Key。請確認已設定於 secrets.toml 或是側邊欄中。",
            "債市焦點": "請設定 API Key。",
            "能源盤後": "---",
            "貴金屬盤後": "---",
            "紐約匯市": "---",
            "台幣焦點": "---"
        }
    
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        prompt = """
        請模擬專業華爾街金融分析師，依據路透社(Reuters)、Yahoo Finance與TradingView的最新市場動態與總體經濟趨勢，產出今日專業的「TIS晨報-新聞摘要」。
        請嚴格分成以下六大板塊，針對當天市場標的與相關資訊進行深度結構化整理，以專業流暢的繁體中文撰寫：
        1. 美股焦點
        2. 債市焦點
        3. 能源盤後
        4. 貴金屬盤後
        5. 紐約匯市
        6. 台幣焦點
        
        請務必以 JSON 格式回傳，鍵名必須對應為：us_stock, bond_market, energy, precious_metals, forex, twd。
        """
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': '你是一個頂尖的財經主編與總經分析師。'},
                {'role': 'user', 'content': prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = completion.choices[0].message.content
        content_dict = json.loads(raw_content)
        return {
            "美股焦點": content_dict.get("us_stock", ""),
            "債市焦點": content_dict.get("bond_market", ""),
            "能源盤後": content_dict.get("energy", ""),
            "貴金屬盤後": content_dict.get("precious_metals", ""),
            "紐約匯市": content_dict.get("forex", ""),
            "台幣焦點": content_dict.get("twd", "")
        }
    except Exception as e:
        return {
            "美股焦點": f"❌ API 呼叫發生錯誤: {str(e)}\n\n💡 提示：請確認您的阿里雲 API Key 是否正確且帳戶餘額充足。",
            "債市焦點": "請檢查 API 設定。",
            "能源盤後": "---",
            "貴金屬盤後": "---",
            "紐約匯市": "---",
            "台幣焦點": "---"
        }

current_time = datetime.now()
is_7am_refresh = (current_time.hour == 7 and current_time.minute < 5)

if st.sidebar.button("🔄 立即手動更新新聞摘要") or 'news_cache' not in st.session_state or is_7am_refresh:
    with st.spinner("正在呼叫阿里雲 Qwen 整合全球財經新聞來源並生成摘要..."):
        st.session_state['news_cache'] = generate_ai_news_summary(api_key, model_choice)
        st.session_state['last_updated'] = current_time.strftime('%Y-%m-%d %H:%M:%S')

st.caption(f"📌 新聞摘要最後更新時間：{st.session_state.get('last_updated', '尚未更新')} ｜ 每日早上 07:00 自動刷新快取")

news_data = st.session_state.get('news_cache', {})

# 呈現六大新聞摘要板塊
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
