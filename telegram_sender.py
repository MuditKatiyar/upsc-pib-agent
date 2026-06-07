import requests

def send_telegram(token, chat_id, text):

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    chunks = [
        text[i:i+3500]
        for i in range(0, len(text), 3500)
    ]

    for chunk in chunks:

        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk
            }
        )
