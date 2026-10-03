@st.cache_data(ttl=3600)
def fetch_market_data_robust(tickers_dict, target_date_str, api_key, base_url, model):
    data = []
    target_dt = pd.to_datetime(target_date_str)
    # 往前抓取 20 天，確保能跨越週末與連續假期
    start_dt = target_dt - timedelta(days=20)
    end_dt = target_dt + timedelta(days=1)
    
    missing_items = []
    
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d'))
            if not hist.empty:
                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)
                
                # 篩選小於等於目標日期的資料
                hist = hist[hist.index.date <= target_dt.date()]
                
                if not hist.empty:
                    # 抓取距離目標日期最近的那一天（即最後一筆資料，例如星期五的收盤價）
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
            
    # AI 智慧補齊抓不到或仍為空值的項目
    if missing_items and api_key:
        prompt = f"""
        你是一個專業的金融數據分析師。請根據全球與台灣股市（包含加權指數、櫃買指數、0050、0051等）在最近一個交易日【接近 {target_date_str} 的星期五收盤行情】的真實歷史收盤數據，提供以下缺失標的的精準收盤價、漲跌變動與漲跌幅百分比：
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
