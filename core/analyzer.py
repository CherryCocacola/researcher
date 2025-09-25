# core/analyzer.py
from openai import OpenAI
import base64

class Assistant:
    def __init__(self, config):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model_name

    def analyze_image(self, image):
        try:
            image_bytes = image.read()
            encoded = base64.b64encode(image_bytes).decode("utf-8")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "이미지를 분석하는 전문가입니다. 이 이미지를 분석하여 구성요소(예를 들어 자동차 라면 타이어, 휠, 유리 콜라 라면 콜라원액, 병뚜껑, 병)별로 제조사, 목적, 제작기술, 필요기술, 필요기자재, 시설, 재질 이외에도 분석 가능한 모든 것을 분석합니다."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "1. 이 이미지를 분석해서 모든 기술 항목 별로 ※ 매우 중요: 마크다운 기호 중 다음은 절대 사용하지 마세요 → #, *, =, $, **, ## 대신 아래 기호만 사용 가능:  - 항목 구분에는 '하이픈(-)' 또는 '중간점(·)'만 사용 - 들여쓰기나 강조 표현은 절대 사용하지 말 것  ※ 출력 예시는 다음과 같이 구성: 브랜드: Apple, Samsung  제작기술: 3D 프린팅 조건 1. 기술 항목별로 분류하여 작성 2. 최대 600 tokens 이내로 작성 2. 600 tokens 이내로 기술분석서 작성해주세요."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
                        ]
                    }
                ],
                temperature=0.5,
                max_tokens=600
            )
            summary = response.choices[0].message.content.strip()
            return {"query": summary}

        except Exception as e:
            return {"error": str(e)}

    def assist_from_text(self, text):
        #prompt = f"다음 문장을 기반으로 기술분석서를 작성해주세요. 1. 기술 항목별로 분류하고 마크다운 형식(마크다운 기호 중 #, *, =, $, **, ## 기호는 항목설명에 절대 사용금지 -, · 기호만 사용가능)으로 작성 2. 600 tokens 이내로 기술분석서 작성해주세요.\n\n{text}"
        prompt = f"""다음 문장을 기반으로 모든 항목의 기술분석서를 작성해주세요. ※ 매우 중요: 마크다운 기호 중 다음은 절대 사용하지 마세요 → #, *, =, $, **, ## 대신 아래 기호만 사용 가능:  - 항목 구분에는 '하이픈(-)' 또는 '중간점(·)'만 사용 - 들여쓰기나 강조 표현은 절대 사용하지 말 것  ※ 출력 예시는 다음과 같이 구성: 브랜드: Apple, Samsung  제작기술: 3D 프린팅 조건 1. 기술 항목별로 분류하여 작성 2. 최대 600 tokens 이내로 작성 입력 문장:{text}"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 기술분석서 작성 전문가입니다. 입력한 문장 중 제작가능한 사물에 대해 구성요소(예를 들어 자동차 라면 타이어, 휠, 유리 콜라 라면 콜라원액, 병뚜껑, 병)별로 제조사, 목적, 제작기술, 필요기술, 필요기자재, 시설, 재질 이외에도 분석 가능한 모든 것을 분석합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=600
            )
            summary = response.choices[0].message.content.strip()
            return {"query": summary}

        except Exception as e:
            return {"error": str(e)}
