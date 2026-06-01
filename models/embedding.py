from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('all-MiniLM-L6-v2')
def compute_similarity(req_text, code_text):
    req_emb = model.encode([req_text])
    code_emb = model.encode([code_text])
    score = cosine_similarity(req_emb, code_emb)[0][0]
    return score
