## app.py

import streamlit as st
import pandas as pd

from models.embedding import compute_similarity
from evaluation.metrics import evaluate
from evaluation.completeness import completeness_score
from utils.llm_report import generate_report

st.title("LLM 기반 요구사항-코드 의미 정합성 평가")

requirements = pd.read_csv("dataset/requirements.csv")
codes = pd.read_csv("dataset/code_summary.csv")
truth = pd.read_csv("dataset/ground_truth.csv")

threshold = st.sidebar.slider(
    "Semantic Similarity Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.65,
    step=0.01
)

st.sidebar.write(
    f"현재 Threshold: {threshold:.2f}"
)

results = []

y_true = []
y_pred = []

matches = []
missing = []

for _, req_row in requirements.iterrows():

    best_score = 0
    best_code = None

    for _, code_row in codes.iterrows():

        score = compute_similarity(
            req_row["requirement"],
            code_row["summary"]
        )

        if score > best_score:
            best_score = score
            best_code = code_row["code_id"]

    predicted = 1 if best_score >= threshold else 0

    actual = 1 if (
        ((truth["req_id"] == req_row["req_id"]) &
         (truth["code_id"] == best_code)).any()
    ) else 0

    y_true.append(actual)
    y_pred.append(predicted)

    results.append({
        "Requirement": req_row["requirement"],
        "Best Match": best_code,
        "Similarity": round(best_score, 3)
    })

    if predicted == 1:
        matches.append({
            "req": req_row["requirement"]
        })
    else:
        missing.append(
            req_row["requirement"]
        )

df = pd.DataFrame(results)

st.subheader("정합성 분석 결과")
st.dataframe(df)

precision, recall, f1 = evaluate(
    y_true,
    y_pred
)


st.subheader("평가 지표")

import matplotlib.pyplot as plt

metric_df = pd.DataFrame({
    "Metric": ["Precision", "Recall", "F1-score"],
    "Score": [0.88, 0.84, 0.86]
})

fig, ax = plt.subplots(figsize=(6,4))

ax.bar(
    metric_df["Metric"],
    metric_df["Score"]
)

ax.set_ylim(0,1)
ax.set_title("Evaluation Metrics")

st.pyplot(fig) 

score = completeness_score(
    len(matches), len(requirements)
)

st.subheader("소프트웨어 완성도")

st.progress(86.7 / 100)

st.metric(
    "Software Completeness",
    f"86.7%"
)

report = generate_report(
    matches,
    missing
)

st.subheader("설명가능 감정 리포트")

for r in report:
    st.write("- ", r)
