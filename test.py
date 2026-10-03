import streamlit as st
from openai import OpenAI

st.title("API 測試工具")

# 輸入 API Key
api_key = st.text_input("輸入您的 API Key", type="password", value="sk-ws-H.DHYEEDI.1jmZ.MEQCIFdnlkm9WsuFQifkLXtmeo04Ec_vlQPXrvQ2sudBuQZuAiBgbKJn3u8t42wgtb5cJxGe4LMSHzCr3er67pIdQWxqiW")
model = st.selectbox("選擇模型", ["qwen-max", "qwen-plus", "qwen-turbo"])

if st.button("測試呼叫 API"):
    if not api_key:
        st.error("請先輸入 API Key")
    else:
        try:
            with st.spinner("正在連線至阿里雲..."):
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": "你好，請回覆『API連線成功』"}
                    ]
                )
                
                reply = response.choices[0].message.content
                st.success(f"成功收到回應：{reply}")
        except Exception as e:
            st.error(f"連線失敗，錯誤訊息：{str(e)}")
