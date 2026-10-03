@st.cache_data(ttl=3600)
def fetch_market_data_robust(tickers_dict, target_date_str, api_key, base_url, model):
    data = []
    target_dt = pd.to_datetime(target_date_str)
    # 擴大抓取區間以完美克服跨時區與週末假日對齊問題
    start_dt = target_dt - timedelta(days=5)
    end_dt = target_dt + timedelta(days=2)
    
    missing_items = []
    
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            # 抓取資料並強制將時間的時區資訊清除，避免時區錯置
            hist = t.history(start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'))
            if not hist.empty:
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
            
    # AI 智慧補齊抓不到的項目（如櫃買指數、0050、0051等）
    if missing_items and api_key:
        prompt = f"""
        你是一個專業的金融數據分析師。請根據台灣證券交易所與全球市場在日期【{target_date_str}】的真實歷史收盤行情（包含加權指數、櫃買指數、0050、0051等），提供以下缺失標的的精準收盤價、漲跌變動與漲跌幅百分比：
        缺失標的清單：{json.dumps(missing_items, ensure_ascii=False)}
        
        請務必以 JSON 格式回傳，格式範例：
        {{
          "標的名稱": {{"close": "123.45", "change": "+1.23", "pct": "+1.00%"}}
        }}
        """
        messages = [{'role': 'system', 'content': '你是一個精通全球與台股行情的金融AI。'}, {'role': 'user', 'content': prompt}]
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
