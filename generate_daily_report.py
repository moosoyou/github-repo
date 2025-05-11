import os
import requests
import json
import logging
import xml.etree.ElementTree as ET
import re

# --- Config ---
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
BIOSPACE_RSS_URL = 'https://www.biospace.com/all-news.rss'
FIRECRAWL_BASE = 'https://api.firecrawl.dev/v1'

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# 우선 포함 키워드 (정책/기업/기술/성과/임상/투자/파트너십 등)
INCLUDE_KEYWORDS = [
    'clinical', 'fda', 'approval', 'partnership', 'acquisition', 'investment', 'trial', 'data', 'launch', 'deal', 'collaboration',
    'policy', 'regulation', 'act', 'bill', 'guidance', 'order', 'agreement', 'contract',
    '신약', '임상', '승인', '파트너십', '투자', '인수', '합병', '기술', '성과', '계약', '라이선스', '정책', '규제', '법', '지침', '명령'
]
# 정책 관련 키워드 (포함 우선)
POLICY_KEYWORDS = [
    'policy', 'regulation', 'act', 'bill', 'guidance', 'order', '정책', '규제', '법', '지침', '명령'
]
# 제외 키워드 (인력감축/해고/고용/시장동향 등)
EXCLUDE_KEYWORDS = [
    'layoff', 'job', 'market', 'cut', 'restructuring', 'employment', 'hiring', 'fired', 'termination',
    '고용', '해고', '감원', '구조조정', '일자리', '실업', '채용', '퇴사', '정리해고', '고용시장', '구직'
]

def get_news_urls_rss(n=25):
    resp = requests.get(BIOSPACE_RSS_URL)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = root.findall('.//item')
    urls = []
    for item in items[:n]:
        link = item.find('link')
        if link is not None and link.text:
            urls.append(link.text.strip())
    logging.info(f'RSS로 기사 URL {len(urls)}개 추출: {urls}')
    return urls

def get_article_content(url):
    api_url = f'{FIRECRAWL_BASE}/scrape'
    headers = {'Authorization': f'Bearer {FIRECRAWL_API_KEY}', 'Content-Type': 'application/json'}
    payload = {
        "url": url,
        "formats": ["markdown"]
    }
    resp = requests.post(api_url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json().get('data', {})
    title = data.get('metadata', {}).get('title', '')
    body = data.get('markdown', '')
    return title, body

def contains_keyword(text, keywords):
    text_lower = text.lower()
    for kw in keywords:
        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text_lower):
            return True
    return False

def main():
    logging.info('BioSpace RSS+Firecrawl로 뉴스 5개(정책/기업/기술/성과/임상/투자/파트너십 위주) 클리핑 중...')
    urls = get_news_urls_rss(25)
    articles = []
    for i, url in enumerate(urls):
        logging.info(f'[{i+1}/{len(urls)}] 기사 크롤링: {url}')
        try:
            title, body = get_article_content(url)
        except Exception as e:
            logging.warning(f'기사 크롤링 실패: {e}')
            continue
        if not title or not body:
            logging.warning('기사 본문 추출 실패, 건너뜀')
            continue
        articles.append({'url': url, 'title': title, 'body': body})

    # 필터링: 정책/기업/기술/성과/임상/투자/파트너십 등 키워드 포함 + (정책 키워드가 있으면 제외키워드 무시)
    filtered = []
    for art in articles:
        t = art['title'] + ' ' + art['body']
        has_policy = contains_keyword(t, POLICY_KEYWORDS)
        has_include = contains_keyword(t, INCLUDE_KEYWORDS)
        has_exclude = contains_keyword(t, EXCLUDE_KEYWORDS)
        if has_policy:
            filtered.append(art)
        elif has_include and not has_exclude:
            filtered.append(art)
        if len(filtered) >= 5:
            break
    # 부족하면 나머지에서 채움
    if len(filtered) < 5:
        for art in articles:
            if art not in filtered:
                filtered.append(art)
            if len(filtered) >= 5:
                break
    with open('clipped_news.json', 'w', encoding='utf-8') as f:
        json.dump(filtered[:5], f, ensure_ascii=False, indent=2)
    logging.info('clipped_news.json 생성 완료!')

if __name__ == '__main__':
    main() 