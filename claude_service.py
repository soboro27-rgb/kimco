import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


async def generate_report(prompt: str, api_key: str = None) -> str:
    key = api_key or ANTHROPIC_API_KEY
    if not key or key == "여기에_API_키_입력":
        return "[데모 모드] Claude API 키가 설정되지 않았습니다.\n\n대시보드의 'Claude API 연결' 버튼을 눌러 API 키를 입력해주세요.\n\n--- 샘플 리포트 ---\n\n■ 세무 분석 요약\n고객이 제공한 자료를 바탕으로 검토한 결과, 주요 세무 이슈 및 절세 포인트를 아래와 같이 정리합니다.\n\n1. 소득 구조 분석\n   - 사업 소득 및 투자 소득 분류 필요\n   - 세금 공제 항목 최적화 검토 권장\n\n2. 절세 포인트\n   - Retirement Plan(SEP-IRA 등) 활용\n   - Business Expense 분류 정확성 확인\n\n3. 주의사항\n   - 신고 기한 준수\n   - 추정세액 납부 일정 확인\n\n본 리포트는 데모용 샘플입니다."

    import anthropic
    client = anthropic.Anthropic(api_key=key)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Claude API 오류: {str(e)}"
