import os

from news_fetcher import (
    get_pib_news,
    extract_article_text
)

from gemini_engine import explain_news

from telegram_sender import send_telegram

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)

print("Starting UPSC AI Agent")

news_list = get_pib_news()

print(
    f"Articles Found: {len(news_list)}"
)

if len(news_list) == 0:

    send_telegram(
        BOT_TOKEN,
        CHAT_ID,
        "No articles found today."
    )

    quit()

for index, news in enumerate(news_list, start=1):

    print(
        f"Processing {index}"
    )

    article_text = extract_article_text(
        news["link"]
    )

    if len(article_text) < 100:

        continue

    explanation = explain_news(
        GEMINI_API_KEY,
        news["title"],
        article_text
    )

    final_message = (
        f"NEWS {index}\n\n"
        + explanation
    )

    send_telegram(
        BOT_TOKEN,
        CHAT_ID,
        final_message
    )

print("Completed Successfully")
