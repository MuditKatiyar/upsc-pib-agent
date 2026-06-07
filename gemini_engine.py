from google import genai

def explain_news(api_key, title, article_text):

    prompt = f"""
You are a senior UPSC faculty member.

Explain the following news article in a logical and easy-to-understand way.

News Title:
{title}

Article:
{article_text}

Provide output in this format:

1. NEWS TITLE

2. WHAT HAPPENED?
Explain simply.

3. BACKGROUND
Explain concepts needed to understand this news.

4. WHY IS IT IN NEWS?

5. WHY IS IT IMPORTANT FOR INDIA?

6. UPSC RELEVANCE
Prelims:
GS Paper:
Essay:
Interview:

7. KEY FACTS

8. PRELIMS MCQ

9. MAINS QUESTION

Use simple language.
Avoid technical jargon.
"""

    client = genai.Client(
        api_key=api_key
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text
