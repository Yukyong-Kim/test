import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from collections import Counter
from textblob import TextBlob, Word
import matplotlib.pyplot as plt
import random

st.set_page_config(page_title="📰 News Comparison Tool", layout="wide")

# Initialize session state
if "articles" not in st.session_state:
    st.session_state.articles = []
if "selected_articles" not in st.session_state:
    st.session_state.selected_articles = []

section_urls = {
    "Technology": "https://www.bbc.com/news/technology",
    "Health": "https://www.bbc.com/news/health",
    "Science": "https://www.bbc.com/news/science_and_environment"
}

# Sidebar for input
st.sidebar.title("🔎 News Fetching")
selected_section = st.sidebar.selectbox("Select News Section", list(section_urls.keys()))
search_term = st.sidebar.text_input("Search Keywords (up to 3)")
fetch_btn = st.sidebar.button("Fetch Articles")

# Helper functions
def classify_tone(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"

def extract_keywords(text, top_n=5):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stop_words = set(["this", "that", "with", "from", "have", "will", "which", "about", "their",
        "they", "been", "were", "would", "could", "should", "while", "after", "before",
        "said", "says", "news", "report", "more", "than", "some", "most", "other",
        "what", "when", "where", "your", "also", "just", "over", "into", "under", "against",
        "there", "these", "those", "however", "because", "since", "being", "through"])
    words = [w for w in words if w not in stop_words]
    freq = Counter(words)
    keywords = [word for word, _ in freq.most_common(top_n)]
    while len(keywords) < top_n:
        keywords.append("relevant")
    return keywords

def summarize_article(content, max_words=100):
    intro_cues = ["This article discusses", "According to the article,",
        "The report focuses on", "In this article,", "It is reported that"]
    conclusion_cues = ["In conclusion,", "To summarize,", "Overall,", "Ultimately,", "In essence,"]
    enumerate_cues = ["First,", "Second,", "In addition,", "Furthermore,", "Lastly,"]
    sentences = re.split(r'(?<=[.!?]) +', content.strip())
    if len(sentences) >= 5:
        enumerated = [f"{enumerate_cues[i]} {sentences[i]}" for i in range(min(4, len(sentences)))]
        intro = f"{random.choice(intro_cues)} {sentences[0].lower()}"
        outro = f"{random.choice(conclusion_cues)} {sentences[-1]}"
        summary = intro + ' ' + ' '.join(enumerated) + ' ' + outro
        return ' '.join(summary.split()[:max_words]) + ('...' if len(summary.split()) > max_words else '')
    elif len(sentences) >= 3:
        intro = f"{random.choice(intro_cues)} {sentences[0].lower()}"
        outro = f"{random.choice(conclusion_cues)} {sentences[-1]}"
        summary = intro + ' ' + sentences[1] + ' ' + outro
        return ' '.join(summary.split()[:max_words]) + ('...' if len(summary.split()) > max_words else '')
    elif sentences:
        summary = f"{random.choice(intro_cues)} {sentences[0]}"
        return ' '.join(summary.split()[:max_words]) + ('...' if len(summary.split()) > max_words else '')
    return "Summary not available."

# Fetch articles
if fetch_btn:
    guide_url = section_urls[selected_section]
    headers = {"User-Agent": "Mozilla/5.0"}
    terms = [t.lower() for t in search_term.strip().split()[:3]] if search_term.strip() else []
    st.session_state.articles.clear()

    try:
        response = requests.get(guide_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        headlines = soup.select("a[href^='/news']")
        seen = set()
        temp_articles = []

        for tag in headlines:
            href = tag.get("href")
            full_url = href if href.startswith("http") else f"https://www.bbc.com{href}"
            title = tag.get_text(strip=True)
            if not title or full_url in seen:
                continue
            seen.add(full_url)

            try:
                article_response = requests.get(full_url, headers=headers)
                article_soup = BeautifulSoup(article_response.text, "html.parser")
                time_tag = article_soup.find("time")
                pub_date = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00")) if time_tag and time_tag.has_attr("datetime") else None
                paragraphs = article_soup.find_all("p")
                content_text = " ".join(p.get_text() for p in paragraphs)
            except:
                continue

            if not content_text.strip():
                continue

            if terms and not any(term in f"{title} {content_text}".lower() for term in terms):
                continue

            tone_label = classify_tone(title + " " + content_text)
            temp_articles.append({
                "title": title,
                "source": "BBC",
                "date": pub_date,
                "content": content_text,
                "url": full_url,
                "tone": tone_label
            })

        dated = sorted([a for a in temp_articles if a["date"]], key=lambda x: x["date"], reverse=True)
        st.session_state.articles.extend(dated[:10])
        if len(st.session_state.articles) < 6:
            unknown = [a for a in temp_articles if not a["date"]]
            st.session_state.articles.extend(unknown[:(6 - len(st.session_state.articles))])

        st.success(f"Fetched {len(st.session_state.articles)} articles")
    except Exception as e:
        st.error(f"Error fetching articles: {e}")

# Display article table
if st.session_state.articles:
    st.subheader("📄 Articles")
    titles = [f"{a['title']} ({a['date'].strftime('%Y-%m-%d') if a['date'] else 'Unknown'}) - {a['tone']}" for a in st.session_state.articles]
    selected = st.multiselect("Select Articles", titles)
    st.session_state.selected_articles = [a for a in st.session_state.articles if f"{a['title']}" in str(selected)]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁 View Selected"):
            for a in st.session_state.selected_articles:
                st.markdown(f"### {a['title']}")
                st.markdown(f"**Source**: {a['source']} | **Date**: {a['date']}")
                st.text_area("Content", a['content'], height=200)

    with col2:
        if st.button("📊 Analyze Tone"):
            fig, ax = plt.subplots(figsize=(8, 5))
            sentiments = {"Positive": [], "Negative": [], "Neutral": []}
            for article in st.session_state.selected_articles:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', article['content'].lower())
                counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
                for word in words:
                    polarity = TextBlob(Word(word)).sentiment.polarity
                    if polarity > 0.1:
                        counts["Positive"] += 1
                    elif polarity < -0.1:
                        counts["Negative"] += 1
                    else:
                        counts["Neutral"] += 1
                for tone in ["Positive", "Negative", "Neutral"]:
                    sentiments[tone].append(counts[tone])
                st.write(f"**{article['title']}**")
                st.write(counts)
            labels = [a['title'][:15] + '...' for a in st.session_state.selected_articles]
            x = range(len(labels))
            bar_width = 0.25
            for i, tone in enumerate(["Positive", "Negative", "Neutral"]):
                ax.bar([p + i * bar_width for p in x], sentiments[tone], width=bar_width, label=tone)
            ax.set_xticks([p + bar_width for p in x])
            ax.set_xticklabels(labels, rotation=30, ha="right")
            ax.set_ylabel("Word Count")
            ax.set_title("Sentiment Word Frequencies")
            ax.legend()
            st.pyplot(fig)

    if st.button("📝 Generate Draft"):
        draft = "📝 **News Comparison Draft**\n\n"
        tones = {"Positive": [], "Negative": [], "Neutral": []}
        for a in st.session_state.selected_articles:
            date_str = a['date'].strftime('%Y-%m-%d') if a['date'] else "Unknown"
            keywords = extract_keywords(a['content'])
            summary = summarize_article(a['content'])
            draft += f"• **{a['title']}** ({a['source']} - {date_str})\n"
            draft += f"  → Tone: {a['tone']}\n"
            draft += f"  → Keywords: {', '.join(keywords)}\n"
            draft += f"  → Summary: {summary}\n\n"
            tones[a['tone']].append(a['title'])
        draft += "\n---\n\n📌 **Analysis Summary**\n"
        for tone, titles in tones.items():
            if titles:
                draft += f"- {tone} articles: {len(titles)} ({', '.join(titles[:3])})\n"
        st.text_area("Draft", draft, height=400)

    if len(st.session_state.selected_articles) == 2 and st.button("🔍 Compare 2 Articles"):
        a1, a2 = st.session_state.selected_articles
        k1 = extract_keywords(a1['content'], top_n=4)
        k2 = extract_keywords(a2['content'], top_n=4)
        comparison = f"# 📘 Comparative Analysis\n\n## Introduction\n"
        comparison += f"Comparing \"{a1['title']}\" and \"{a2['title']}\".\n\n"
        comparison += f"## Tone Comparison\n"
        comparison += f"Article 1 is *{a1['tone'].lower()}*, using words like {k1[0]}, {k1[1]}.\n"
        comparison += f"Article 2 is *{a2['tone'].lower()}*, with terms such as {k2[0]}, {k2[1]}.\n\n"
        comparison += f"## Framing Analysis\n"
        comparison += f"Article 1 frames the issue as a "
        comparison += "breakthrough" if a1['tone'] == "Positive" else "controversial issue" if a1['tone'] == "Negative" else "balanced development"
        comparison += f", while Article 2 highlights "
        comparison += "benefits" if a2['tone'] == "Positive" else "concerns" if a2['tone'] == "Negative" else "neutral implications"
        comparison += ".\n\n## Conclusion\nThe two articles provide contrasting perspectives."
        st.text_area("Comparison Report", comparison, height=300)
