"""Render the actual Controller/Service/Repository source into readable PNGs."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/main/java/com/umc/study'
OUTPUT = ROOT / 'results'
MONO = 'C:/Windows/Fonts/consola.ttf'
KOREAN = 'C:/Windows/Fonts/malgun.ttf'
BOLD = 'C:/Windows/Fonts/malgunbd.ttf'


def render(prefix, title, filename):
    files = [SOURCE/f'{layer}/{prefix}{suffix}.java' for layer, suffix in
             [('controller', 'Controller'), ('service', 'Service'), ('repository', 'Repository')]]
    listing = [(p.relative_to(ROOT).as_posix(), p.read_text(encoding='utf-8').splitlines()) for p in files]
    heights = [len(lines)*27+82 for _, lines in listing]
    height = 190 + sum(heights) + 30*len(heights) + 55
    im = Image.new('RGB', (1800, height), '#f3f6fa')
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, 1800, 158), fill='#14273e')
    draw.text((45, 23), 'UMC 3주차 · 직접 작성한 핵심 코드', font=ImageFont.truetype(KOREAN, 26), fill='#a8c3e5')
    draw.text((45, 67), title, font=ImageFont.truetype(BOLD, 37), fill='white')
    draw.text((45, 119), '현재 작업 폴더의 실제 Java 원본 · Controller → Service → Repository',
              font=ImageFont.truetype(KOREAN, 21), fill='#d4e0ee')
    y = 185
    for (path, lines), panel_height in zip(listing, heights):
        draw.rounded_rectangle((36, y, 1764, y+panel_height), 14, fill='white')
        draw.text((58, y+16), path, font=ImageFont.truetype(MONO, 22), fill='#44678c')
        for i, line in enumerate(lines, 1):
            yy = y+59+(i-1)*27
            draw.text((60, yy), f'{i:>3}', font=ImageFont.truetype(MONO, 21), fill='#90a3b8')
            colour = '#176149' if line.lstrip().startswith('//') else '#18314b'
            code_font = KOREAN if any(ord(c)>127 for c in line) else MONO
            draw.text((125, yy), line, font=ImageFont.truetype(code_font, 21), fill=colour)
        y += panel_height+30
    draw.text((45, y), '출처: week03/src/main/java/com/umc/study · 원본 코드의 내용과 줄 번호를 그대로 표시',
              font=ImageFont.truetype(KOREAN, 20), fill='#52657b')
    im.save(OUTPUT/filename)
    print(filename)


render('Book', '도서 조회·등록 및 카테고리 조회 — 세 계층 핵심 코드', 'core-book-code.png')
render('Rental', '신규 도서 대여 기록 생성 — 세 계층 핵심 코드', 'core-rental-code.png')
