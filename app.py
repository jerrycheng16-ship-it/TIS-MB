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

# 側邊欄：系統設定與歷史日期篩選
st.sidebar.header("⚙️ 系統設定與日期篩選")
selected_date = st.sidebar.date_input("選擇檢視收盤日期", datetime.now().date())

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

# 定義標的清單
group1_indices = {
    "道瓊工業指數": "^DJI", "那斯達克指數": "^IXIC", "標普500指數": "^GSPC",
    "費城半導體指數": "^SOX", "羅素2000指數": "^RUT", "英國FTSE 100": "^FTSE",
    "德國DAX指數": "^GDAXI", "法國CAC指數": "^FCHI", "道瓊歐洲600指數": "^STOXX"
}

group2_indices = {
    "日經225指數": "^N225", "南韓KOSPI指數": "^KS11", "恆生指數": "^HSI",
    "上證指數": "000001.SS", "新加坡STI指數": "^STI", "泰國曼谷SET指數": "^SET.BK",
    "富時馬來西亞指數": "^KLSE", "菲律賓綜合指數": "PSEI.PS", "印尼雅加達指數": "^JKSE"
}

group3_indices = {
    "加權指數": "^TWII", "不含電子指數": "^TWII", "上櫃指數": "^TWOII",
    "0050": "0050.TW", "0051": "0051.TW", "MSCI全球指數": "URTH",
    "歐洲Stoxx 50": "^STOXX50E", "MSCI新興市場": "EEM", "MSCI拉丁美洲": "ILF"
}

comm1 = {
    "Crude Oil 原油": "CL=F", "Natural Gas 天然氣": "NG=F", "Gold 黃金": "GC=F",
    "Silver 白銀": "SI=F", "Copper 銅": "HG=F"
}

comm2 = {
    "CRB 商品指數": "DBC", "Corn 玉米": "ZC=F", "Wheat 小麥": "ZW=F",
    "Soybean 黃豆": "ZS=F", "Cotton 棉花": "CT=F"
}

comm3 = {
    "DXY 美元指數": "DX-Y.NYB", "BDI運價指數": "BDRY", "VIX 指數": "^VIX",
    "VXN 指數": "^VXN", "美國10年公債殖利率": "^TNX"
}

def call_qwen_api(messages_list, key, b_url, chosen_model):
    if not key:
        return None, "尚未偵測到 API Key。"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key.strip(), base_url=b_url.strip())
        models_to_try = [chosen_model, 'qwen-max', 'qwen-plus', 'qwen-turbo']
        models_to_try = list(dict.fromkeys(models_to_try))
        
        for m_name in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=m_name, messages=messages_list, temperature=0.1, response_format={"type": "json_object"}
                )
                if response and response.choices:
                    return response.choices[0].message.content, None
            except Exception:
                time.sleep(0.5)
        return None, "所有模型嘗試皆失敗"
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=3600)
def fetch_market_data_robust(tickers_dict, target_date_str, api_key, base_url, model):
    data = []
    target_dt = pd.to_datetime(target_date_str)
    start_dt = target_dt - timedelta(days=20)
    end_dt = target_dt + timedelta(days=2)
    
    missing_items = []
    
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'))
            if not hist.empty:
                # 消除時區落差導致的對齊錯誤
                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)
                hist = hist[hist.index.date <= target_dt.date()]
                if not hist.empty:
                    close = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else close
                    change = close - prev
                    pct_change = (change / prev) * 100 if prev != 0 else 0.0
                    
                    data.append({
                        "指數/商品": name,
                        "收盤價": f"{close:,.2f}",
                        "變動": f"{change:+,.2f}",
                        "(%)": f"{pct_change:+.2f}%"
                    })
                    continue
            missing_items.append(name)
        except Exception:
            missing_items.append(name)
            
    # AI 智慧補齊抓不到或 nan 的項目
    if missing_items and api_key:
        prompt = f"""
        你是一個專業的金融數據分析師。請根據全球與台灣股市（包含加權指數、櫃買指數、0050、0051等）在日期【{target_date_str}】的真實歷史收盤行情，提供以下缺失標的的精準收盤價、漲跌變動與漲跌幅百分比：
        缺失標的清單：{json.dumps(missing_items, ensure_ascii=False)}
        
        請務必以 JSON 格式回傳，格式範例：
        {{
          "標的名稱": {{"close": "123.45", "change": "+1.23", "pct": "+1.00%"}}
        }}
        """
        messages = [{'role': 'system', 'content': '你是一個精通全球股市與台股行情的金融AI。'}, {'role': 'user', 'content': prompt}]
        res_str, _ = call_qwen_api(messages, api_key, base_url, model)
        if res_str:
            try:
                ai_data = json.loads(res_str)
                for name in missing_items:
                    if name in ai_data:
                        val = ai_data[name]
                        data.append({
                            "指數/商品": name,
                            "收盤價": val.get("close", "N/A"),
                            "變動": val.get("change", "N/A"),
                            "(%)": val.get("pct", "N/A")
                        })
                    else:
                        data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
            except Exception:
                for name in missing_items:
                    data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
        else:
            for name in missing_items:
                data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
                
    ordered_data = []
    data_dict = {item["指數/商品"]: item for item in data}
    for name in tickers_dict.keys():
        if name in data_dict and data_dict[name]["收盤價"] not in ["nan", "NaN", "N/A", None]:
            ordered_data.append(data_dict[name])
        else:
            ordered_data.append({"指數/商品": name, "收盤價": "N/A", "變動": "N/A", "(%)": "N/A"})
            
    return pd.DataFrame(ordered_data)

st.markdown(f'<div class="section-header">全球主要股市與商品收盤表現（基準日：{selected_date}）</div>', unsafe_allow_html=True)
col_i1, col_i2, col_i3 = st.columns(3)

with col_i1:
    st.markdown("**美、歐股市**")
    st.dataframe(fetch_market_data_robust(group1_indices, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

with col_i2:
    st.markdown("**亞洲股市**")
    st.dataframe(fetch_market_data_robust(group2_indices, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

with col_i3:
    st.markdown("**台灣與國際指數**")
    st.dataframe(fetch_market_data_robust(group3_indices, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

st.markdown('<div class="section-header">大宗商品、匯率與債市表現</div>', unsafe_allow_html=True)
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.markdown("**金屬能源 (Commodity)**")
    st.dataframe(fetch_market_data_robust(comm1, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

with col_c2:
    st.markdown("**農作商品 (Commodity)**")
    st.dataframe(fetch_market_data_robust(comm2, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

with col_c3:
    st.markdown("**其他商品與指標**")
    st.dataframe(fetch_market_data_robust(comm3, str(selected_date), api_key, base_url_input, model_choice), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown(f'<div class="main-title">TIS晨報 - 新聞摘要 ({selected_date})</div>', unsafe_allow_html=True)

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
