import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import json

# 頁面設定
st.set_page_config(
    page_title="TIS晨報 - 市場收盤與新聞摘要",
    page_icon="📈",
    layout="wide"
)

# 自訂 CSS 樣式，精確對齊專業財經終端機與圖片排版
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
    /* 調整表格字型與邊框，貼近圖片簡潔風格 */
    dataframe {
        font-size: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">TIS晨報 - 重要市場收盤表現</div>', unsafe_allow_html=True)

# 側邊欄：API 設定與定時更新資訊
st.sidebar.header("⚙️ 系統設定")
api_key = st.sidebar.text_input("請輸入阿里雲 API Key (DashScope)", type="password", value=os.environ.get("DASHSCOPE_API_KEY", ""))
model_choice = st.sidebar.selectbox("選擇阿里雲模型", ["qwen-max", "qwen-plus", "qwen-turbo"])

st.sidebar.markdown("---")
st.sidebar.markdown("### ⏰ 自動更新機制")
st.sidebar.write("系統設定於 **每天早上 07:00** 自動重新整理並呼叫 AI 生成最新晨報摘要。")

# 依照圖片的三大欄位分類定義標的
group1_tickers = {
    "道瓊工業": "^DJI",
    "標普 500": "^GSPC",
    "那斯達克": "^IXIC",
    "費城半導體": "^SOX",
    "羅素 2000": "^RUT",
    "FTSE 100": "^FTSE",
    "DAX": "^GDAXI",
    "CAC 40": "^FCHI",
    "Stoxx 600": "^STOXX"
}

group2_tickers = {
    "日經 225": "^N225",
    "KOSPI": "^KS11",
    "上證指數": "000001.SS",
    "香港恆生": "^HSI",
    "STI": "^STI",
    "泰國 SET": "^SETI"
}

group3_tickers = {
    "Crude Oil (WTI)": "CL=F",
    "Natural Gas": "NG=F",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "DXY 美元指數": "DX-Y.NYB",
    "US 10Y Yield": "^TNX",
    "VIX": "^VIX",
    "0050": "0050.TW"
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
                    "市場/商品": name,
                    "收盤價": f"{close:,.2f}",
                    "漲跌": f"{change:+,.2f}",
                    "漲跌幅 (%)": f"{pct_change:+.2f}%"
                })
            else:
                data.append({"市場/商品": name, "收盤價": "N/A", "漲跌": "N/A", "漲跌幅 (%)": "N/A"})
        except Exception:
            data.append({"市場/商品": name, "收盤價": "N/A", "漲跌": "N/A", "漲跌幅 (%)": "N/A"})
    return pd.DataFrame(data)

# 三欄式並排呈現市場表現（對應圖片的三大區塊格式）
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown('<div class="section-header">主要美股與歐股</div>', unsafe_allow_html=True)
    df1 = fetch_market_data(group1_tickers)
    st.dataframe(df1, use_container_width=True, hide_index=True)

with col_m2:
    st.markdown('<div class="section-header">亞太主要股市</div>', unsafe_allow_html=True)
    df2 = fetch_market_data(group2_tickers)
    st.dataframe(df2, use_container_width=True, hide_index=True)

with col_m3:
    st.markdown('<div class="section-header">商品、匯率與波動率</div>', unsafe_allow_html=True)
    df3 = fetch_market_data(group3_tickers)
    st.dataframe(df3, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown('<div class="main-title">TIS晨報 - 新聞摘要 (基於路透、Yahoo財經、TradingView與阿里雲 Qwen AI)</div>', unsafe_allow_html=True)

# 透過阿里雲 DashScope API 生成新聞摘要
def generate_ai_news_summary(api_key, model):
    if not api_key:
        return {
            "美股焦點": "⚠️ 請在左側邊欄輸入您的阿里雲 API Key (DashScope)，以自動生成新聞摘要。",
            "債市焦點": "請輸入 API Key 後點擊更新。",
            "能源盤後": "請輸入 API Key 後點擊更新。",
            "貴金屬盤後": "請輸入 API Key 後點擊更新。",
            "紐約匯市": "請輸入 API Key 後點擊更新。",
            "台幣焦點": "請輸入 API Key 後點擊更新。"
        }
    
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        prompt = """
        請模擬專業華爾街金融分析師，依據路透社(Reuters)、Yahoo Finance與TradingView的最新市場動態與總體經濟趨勢，產出今日專業的「TIS晨報-新聞摘要」。
        請嚴格分成以下六大板塊，以結構化、專業流暢的繁體中文撰寫：
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
            "美股焦點": f"❌ API 呼叫發生錯誤: {str(e)}\n\n💡 請檢查：\n1. 是否輸入了正確的「阿里雲 DashScope API Key」（非 OpenAI Key）。\n2. 帳戶餘額是否充足。\n3. 網路連線是否正常。",
            "債市焦點": "請確認 API Key 是否有效。",
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
