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

   
    
BioSpace 기사 제목: {title}

아래 기사 본문을 읽고, 핵심 주체(회사/인물/기관,영어로)와 주요 내용을 한국어로 2~4개 최대한 구체적(임상, 재무, 인용 등) 불릿포인트로 핵심만 요약해줘. 
각 불릿포인트는 최대한 데이터 기반, 인용, 수치, 임상결과 등 구체적으로 작성. 
포맷은 아래 형식 예시처럼 꼭 맞춰주면 좋겠어

기사 본문:
{body}

형식 예시:
▷ Lilly (#RNA)
- Eli Lilly, 한국 Rznomics와 RNA 편집 기반 청력 손실 치료제 공동개발 계약(총 13억 달러 규모)
- 선급금 4,000만 달러, 임상·상업화 마일스톤 및 로열티 포함
- Rznomics의 RNA 편집 플랫폼, 기존 유전자치료 한계 극복 기대
- Lilly, 2024년 RNA·유전자치료 분야에만 30억 달러 이상 투자
<https://tinyurl.com/yoqnczm3>
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
