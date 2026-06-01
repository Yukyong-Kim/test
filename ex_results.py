import matplotlib.pyplot as plt

# Threshold 값
thresholds = [0.4, 0.5, 0.6, 0.7, 0.8]

# 실험 결과 예시
precisions = [0.72, 0.81, 0.88, 0.91, 0.95]
recalls = [0.95, 0.91, 0.84, 0.72, 0.60]
f1_scores = [0.82, 0.86, 0.86, 0.80, 0.73]

# 그래프 크기 설정
plt.figure(figsize=(8, 5))

# Precision 그래프
plt.plot(
    thresholds,
    precisions,
    marker='o',
    linewidth=2,
    label='Precision'
)

# Recall 그래프
plt.plot(
    thresholds,
    recalls,
    marker='s',
    linewidth=2,
    label='Recall'
)

# F1-score 그래프
plt.plot(
    thresholds,
    f1_scores,
    marker='^',
    linewidth=2,
    label='F1-score'
)

# 제목 및 축 라벨
plt.title(
    'Threshold Sensitivity Analysis',
    fontsize=14
)

plt.xlabel(
    'Similarity Threshold',
    fontsize=12
)

plt.ylabel(
    'Score',
    fontsize=12
)

# 축 범위
plt.ylim(0, 1.0)

# Grid 표시
plt.grid(True)

# 범례 표시
plt.legend()

# 그래프 출력
plt.show()
