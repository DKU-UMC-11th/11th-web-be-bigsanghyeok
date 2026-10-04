"""Render actual verification logs as clearly labelled reports, not Postman screenshots."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
CASES = json.loads((OUT/'http-results.json').read_text(encoding='utf-8'))
META = json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
FONT = 'C:/Windows/Fonts/malgun.ttf'
BOLD = 'C:/Windows/Fonts/malgunbd.ttf'


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def value_text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


def render(index, filename, title, supplement=None):
    case = CASES[index]
    request_lines = value_text(case['request_body']).splitlines() if case['request_body'] else ['Body 없음']
    response_lines = value_text(case['response']).splitlines()
    content_height = max(len(request_lines), len(response_lines)) * 32 + 95
    extra_height = (len(supplement[1]) * 32 + 100) if supplement else 0
    height = 295 + content_height + extra_height + 115
    image = Image.new('RGB', (1440, height), '#f3f6fa')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1440, 180), fill='#14273e')
    draw.text((48, 27), 'UMC 3주차 · Spring Boot / JdbcTemplate', font=font(24), fill='#a8c3e5')
    draw.text((48, 72), title, font=font(38, True), fill='white')
    draw.text((48, 131), '실제 HTTP 실행 결과 · 원본 로그 기반 검증 보고서', font=font(23), fill='#d4e0ee')
    draw.rounded_rectangle((48, 205, 1392, 268), 12, fill='white')
    draw.text((68, 218), case['method'], font=font(25, True), fill='#147d5c')
    draw.text((165, 219), case['url'], font=font(25), fill='#23374d')
    draw.rounded_rectangle((1230, 214, 1374, 259), 9, fill='#e3f5ed')
    draw.text((1250, 220), str(case['status'])+' '+('Created' if case['status']==201 else 'OK'), font=font(20, True), fill='#10623f')
    y = 293
    for left, right, label, lines in [(48, 656, 'REQUEST BODY', request_lines),
                                      (680, 1392, 'RESPONSE · '+case['content_type'], response_lines)]:
        draw.rounded_rectangle((left, y, right, y+content_height), 13, fill='white')
        draw.text((left+22, y+18), label, font=font(21, True), fill='#4d6684')
        for offset, line in enumerate(lines):
            draw.text((left+22, y+61+offset*32), line, font=font(23), fill='#18314b')
    y += content_height+24
    if supplement:
        draw.rounded_rectangle((48, y, 1392, y+extra_height-16), 13, fill='white')
        draw.text((70, y+17), supplement[0], font=font(23, True), fill='#4d6684')
        for offset, line in enumerate(supplement[1]):
            draw.text((70, y+62+offset*32), line, font=font(23), fill='#18314b')
        y += extra_height
    draw.text((48, y+8), '실행 시각: '+META['executed_at']+'  |  MySQL '+META['mysql_version'], font=font(20), fill='#52657b')
    draw.text((48, y+40), '출처: results/http-results.json · Postman UI 캡처가 아닌 실제 응답 기록의 시각화', font=font(20), fill='#52657b')
    target = OUT / filename
    image.save(target)
    print(target)


render(0, 'practice-get-books.png', '실습 1 — 도서 전체 목록 조회')
new_book = CASES[2]['response'][-1]
render(1, 'practice-post-books.png', '실습 2 — 신규 도서 등록 및 재조회',
       ('등록 후 GET /books 재조회에서 확인한 신규 도서 (응답 일부)', value_text(new_book).splitlines()))
render(3, 'mission-category.png', '필수 미션 1 — 카테고리별 도서 목록 조회')
db_lines = (OUT/'rental-db.tsv').read_text(encoding='utf-8').splitlines()
db = dict(zip(db_lines[0].split('\t'), db_lines[1].split('\t')))
render(7, 'mission-rental.png', '필수 미션 2 — 신규 도서 대여 기록 생성',
       ('실제 MySQL 저장 결과 · results/rental-db.tsv',
        [f'user_id = {db["user_id"]} / book_id = {db["book_id"]} / rental_id = {db["rental_id"]}',
         'rented_at = '+db['rented_at'], 'due_at = '+db['due_at'],
         'returned_at = '+db['returned_at'], '대여 기간 = '+db['duration_seconds']+'초 (정확히 7일)']))
