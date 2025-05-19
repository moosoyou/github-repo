import os
import json
import datetime
import re
import logging
import openai
import requests
import time

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TINYURL_API_KEY = os.getenv('TINYURL_API_KEY')

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def summarize_article(title, body):
    if not OPENAI_API_KEY:
        logging.warning('OPENAI_API_KEY not set, returning first 3 lines as dummy summary.')
        lines = body.split('\n')
        return lines[:3]
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    max_length = 2000
    if len(body) > max_length:
        body = body[:max_length]
    prompt = f"""

You are very talented Daily News Report creator. Read through the biospace news then refer to the format below, and create visually neat news report.
2-3 bullet points including the specifics (whether it be clinial data, deal or etc) in Korean. Make sure the translation is very natural, without hallucination.

기사 본문:
{body}

Format sample:

▷ FDA (#항암제심사 #인력감축)
• FDA, 항암제 자문위(ODAC) 준비 과정에서 인력 감축 여파로 혼란 발생
• 기존 전문 인력 대거 이탈, 자문위 준비에 경험 부족 자원봉사자 투입
• 내부 관계자 “심사 신뢰성·전문성 저하 우려…내주 3건 항암제 심사 일정 차질 가능성”

▷ Bluebird (#바이아웃 #유전자치료제)
• Bluebird, 사모펀드에 인수되며 주주에 현금 유입 확대
• 인수 대가로 기존 주주에 주당 $13.50 현금 지급, 총 거래 규모 6억 달러 이상
• 신약 파이프라인(유전자치료제) 개발 자금 확보 및 구조조정 목적

▷ Biohaven (#신경질환 #FDA연기)
• FDA, Biohaven의 척수소뇌실조증(SCA) 신약 BHV-4157 승인 결정 3개월 연기
• FDA “추가 임상 데이터 필요” 통보, 기존 PDUFA 일정(5월 20일)에서 8월로 연기
• SCA 환자 대상 임상 3상에서 운동기능 개선 효과 입증, 시장 기대감 여전

▷ Sanofi (#미국투자 #공장신설)
• Sanofi, 미국 내 생산시설에 200억 달러 신규 투자 발표
• 인디애나·노스캐롤라이나 등 3개 주에 대규모 공장 신설, 2,500명 신규 고용
• CEO “미국 내 공급망 강화·차세대 백신 생산 역량 확대” 강조

▷ AbbVie (#ADC #폐암신약)
• AbbVie, 항체-약물접합체(ADC) 신약 ‘Teliso-V’로 비소세포폐암(NSCLC) 적응증 FDA 신속 승인
• 임상 2상에서 객관적 반응률(ORR) 35%, 무진행생존기간(PFS) 5.7개월 기록
• 경쟁사 Daiichi Sankyo, AstraZeneca 등과 ADC 시장 주도권 경쟁

"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=400
    )
    summary = response.choices[0].message.content.strip()
    return summary

def shorten_url(url):
    try:
        if TINYURL_API_KEY:
            api_url = f'https://api.tinyurl.com/create'
            headers = {'Authorization': f'Bearer {TINYURL_API_KEY}', 'Content-Type': 'application/json'}
            data = {"url": url}
            resp = requests.post(api_url, headers=headers, json=data)
            if resp.ok:
                return resp.json()['data']['tiny_url']
        # fallback: public endpoint
        resp = requests.get(f'https://tinyurl.com/api-create.php?url={url}')
        if resp.ok:
            return resp.text.strip()
    except Exception as e:
        logging.warning(f'URL 단축 실패: {e}')
    return url

def format_section_block(summary, short_url):
    lines = summary.strip().split('\n')
    hashtags = ''
    if lines and lines[-1].startswith('#'):
        hashtags = lines.pop(-1)
    if hashtags:
        if '(' in lines[0]:
            lines[0] = re.sub(r'\)$', f' {hashtags})', lines[0])
        else:
            lines[0] += f' ({hashtags})'
    lines.append(f'{short_url}')
    return '\n'.join(lines)

def make_daily_report(news_blocks):
    today = datetime.datetime.now()
    header_date = today.strftime('%Y년 %m월 %d일')
    header = f'해외 제약/바이오 소식 {header_date}'
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}},
        {"type": "header", "text": {"type": "plain_text", "text": "🔬 바이오스페이스 데일리 리포트", "emoji": True}},
        {"type": "divider"}
    ]
    blocks.extend(news_blocks)
    return {
        "channel": "research",
        "blocks": blocks
    }

def main():
    logging.info('clipped_news.json → daily_report.json 변환 시작...')
    with open('clipped_news.json', 'r', encoding='utf-8') as f:
        news_items = json.load(f)
    news_blocks = []
    for i, news in enumerate(news_items):
        title = news['title']
        url = news['url']
        body = news['body']
        if not title or not body:
            logging.warning(f'[{i+1}/5] 기사 본문 추출 실패, 건너뜀')
            continue
        summary = summarize_article(title, body)
        short_url = shorten_url(url)
        section_block = {
            "type": "section",
            "text": {"type": "mrkdwn", "text": format_section_block(summary, short_url)}
        }
        news_blocks.append(section_block)
        time.sleep(1) 
    while len(news_blocks) < 5:
        news_blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "(뉴스 없음)"}
        })
    report = make_daily_report(news_blocks[:5])
    with open('daily_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logging.info('daily_report.json 생성 완료!')

if __name__ == '__main__':
    main() 
