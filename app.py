from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from core.config import AppConfig
from core.vector_utils import VectorUtils
from core.recommendation import ResearcherRecommender
from core.analyzer import Assistant
from core.api import search_papers_by_keyword, search_researchers_by_name
from psycopg2.extras import RealDictCursor
from core.db import get_connection

# .env 파일 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)

# 구성 요소 초기화
config = AppConfig()
embedding = VectorUtils(config)
recommender = ResearcherRecommender(embedding, config)
assistant = Assistant(config)

# 라우팅
# 메인 화면 렌더링
@app.route("/")
def index():
    """메인 화면을 렌더링합니다."""
    return render_template("index.html")

# 이미지 업로드 분석(비전)
@app.route("/upload", methods=["POST"])
def upload_image():
    """이미지 파일을 업로드 받아 비전 모델로 분석하고 텍스트 요약을 반환합니다."""
    image = request.files.get("image")
    if not image:
        return jsonify({"error": "이미지를 업로드하세요."}), 400
    return assistant.analyze_image(image)

# 텍스트 어시스트(요약/정리)
@app.route("/assist", methods=["POST"])
def assist_text():
    """텍스트 입력을 받아 요약/정리 결과를 반환합니다."""
    text = request.json.get("text", "")
    if not text:
        return jsonify({"error": "문장을 입력해주세요."}), 400
    return assistant.assist_from_text(text)

# 연구자 추천
@app.route("/recommend", methods=["POST"])
def recommend():
    """사용자 질의를 바탕으로 연구자를 추천하여 점수/사유/키워드 등을 반환합니다."""
    query = request.json.get("query", "")
    if not query:
        return jsonify([])
    results = recommender.recommend(query)
    payload = []
    for item in results:
        payload.append({
            "researcher_id": item["researcher_id"],
            "name": item["name"],
            "score": item["score"],
            "base_score": item["base_score"],
            "impact_bonus": item["impact_bonus"],
            "keyword_bonus": item["keyword_bonus"],
            "research_keywords": item["research_keywords"],
            "paper_keywords": item["paper_keywords"],
            "reason_markdown": item["reason_markdown"],
            "top_papers": item.get("top_papers", []),
        })
    return jsonify(payload)

# 연구자 상세 조회
@app.route("/researchers/<researcher_id>", methods=["GET"])
def researcher_detail(researcher_id):
    """연구자 ID로 상세 프로필 정보를 JSON으로 반환합니다."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT researcher_id,
                           name,
                           department,
                           position,
                           phone,
                           email,
                           major,
                           lab,
                           research_area,
                           career_summary,
                           experience
                      FROM tb_researcher
                     WHERE researcher_id = %s
                    """,
                    (researcher_id,)
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"error": "not found"}), 404
                return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 논문 검색
@app.route("/papers/search", methods=["GET"])
def papers_search():
    """키워드로 논문을 검색합니다."""
    keyword = request.args.get("q", "")
    if not keyword:
        return jsonify([])
    try:
        rows = search_papers_by_keyword(keyword, limit=int(request.args.get("limit", 20)))
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 연구자 검색
@app.route("/researchers/search", methods=["GET"])
def researchers_search():
    """이름으로 연구자를 검색합니다."""
    name = request.args.get("q", "")
    if not name:
        return jsonify([])
    try:
        rows = search_researchers_by_name(name, limit=int(request.args.get("limit", 20)))
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)