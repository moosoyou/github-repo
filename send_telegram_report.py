import os
import json
import requests
import re

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError('TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables.')

# Read the daily report JSON
with open('daily_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)

blocks = report.get('blocks', [])

lines = []
header = None

for block in blocks:
    if block['type'] == 'header' and not header:
        # 첫 header만 사용
        header = block['text']['text']

# Extract MM/DD from header (e.g., '해외 제약/바이오 소식 2025년 05월 11일' -> '05/11')
header_line = ''
if header:
    m = re.match(r"(해외 제약/바이오 소식) (\d{4})년 (\d{2})월 (\d{2})일", header)
    if m:
        title, year, month, day = m.groups()
        header_line = f"<{title} {month}/{day}>"
    else:
        header_line = f"<{header}>"
    lines.append(header_line)
    lines.append("")  # blank line after header

# Collect only the latest 5 news sections
section_blocks = [block for block in blocks if block['type'] == 'section'][:5]

for block in section_blocks:
    text = block['text']['text']
    # Extract main subject (in *...*), hashtags (in (#...)), and the rest
    m = re.match(r"\\*(.+?)\\* ?\\((#[^)]+)\\)\\n(.+)", text, re.DOTALL)
    if m:
        subject, hashtags, rest = m.groups()
        lines.append(f"▷ {subject} ({hashtags})")
        # Split rest into lines, convert '•' to '-', and extract link
        for line in rest.split('\n'):
            line = line.strip()
            if line.startswith('•'):
                lines.append(f"- {line[1:].strip()}")
            elif re.match(r'https?://[^>]+', line):
                lines.append(line)
        lines.append("")  # 항목 간 한 줄 띄우기
    else:
        # fallback: just print the text
        lines.append(text)
        lines.append("")

message = '\n'.join(lines)

# Send to Telegram
url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": message,
    "parse_mode": "Markdown",
    "disable_web_page_preview": True
}

response = requests.post(url, data=payload)

if response.status_code == 200:
    print('✅ Telegram 메시지 전송 성공!')
else:
    print(f'❌ Telegram 전송 실패: {response.status_code} {response.text}') 