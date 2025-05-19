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

Read the news and provide detailed yet compact report. DO NOT HALLUCINATE
Key entity (company/person/institution in English) with detailed yet compact 2-3 bullet points including the main content of the news in Korean (clinical trials, finance, or quotations)
Format all each news in accordance to the sample below. For each news, just include one SHORTENED NEWS LINK.
Make sure the format is identical for all the news that you'll provide in the report.

기사 본문:
{body}

Format sample:
▷ FDA (#항암제심사 #인력감축)
• FDA, 항암제 자문위(ODAC) 준비 과정에서 인력 감축 여파로 혼란 발생
• 기존 전문 인력 대거 이탈, 자문위 준비에 경험 부족 자원봉사자 투입
• 내부 관계자 “심사 신뢰성·전문성 저하 우려…내주 3건 항암제 심사 일정 차질 가능성”
<shortened newslink>

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
