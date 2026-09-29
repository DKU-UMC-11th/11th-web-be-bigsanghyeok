"""Render real MySQL stdout as HTML and draw the ERD JOIN paths."""
from pathlib import Path
import html
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'
META=json.loads((OUT/'verification.json').read_text(encoding='utf-8'))
ESC=html.escape
CSS='''
*{box-sizing:border-box}body{margin:0;background:#f0f4f9;color:#1d2c43;font:16px/1.65 "Malgun Gothic",sans-serif}
main{max-width:1260px;margin:auto;padding:32px}nav{display:flex;gap:20px;font-size:14px;margin-bottom:28px}a{color:#315cb5}
.eyebrow{color:#506786;font-size:14px}h1{font-size:30px;margin:8px 0 12px}h2{font-size:20px;margin:0 0 14px}
.badge{display:inline-block;background:#d7f4e5;color:#126644;padding:3px 13px;border-radius:20px;font-size:13px;font-weight:700}
.meta{color:#63758a;font-size:13px}section{background:white;border:1px solid #d5dfec;border-radius:14px;padding:24px;margin:20px 0}
.grid{display:grid;grid-template-columns:1.05fr 1fr;gap:20px}.grid section{margin-top:0}
pre{font:14px/1.6 Consolas,"Malgun Gothic",monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid #dfe6ee}
th{background:#edf3fa}td{overflow-wrap:anywhere}.check{background:#eaf6f0;border-left:4px solid #208060;padding:14px;margin:20px 0 0}
footer{font-size:13px;color:#64758b;margin-top:12px}.muted{color:#607188}.small{font-size:13px}code{background:#edf2f8;padding:2px 5px;border-radius:4px}
main{padding:18px}body{font-size:14px;line-height:1.4}nav{margin-bottom:10px}h1{font-size:25px;margin:5px 0 8px}
h2{font-size:17px;margin-bottom:8px}section{padding:14px;margin:12px 0}p{margin:8px 0}.grid{gap:14px}
pre{font-size:12px;line-height:1.4}th,td{padding:8px;font-size:13px}.check{padding:10px;margin-top:12px}
footer{font-size:12px}.eyebrow{font-size:12px}.meta{font-size:12px}
.setup section{padding:10px}.setup th,.setup td{padding:4px 8px}
'''
NAV='<nav><a href="00_setup.html">실행 확인</a><a href="03_mission1.html">미션 1</a><a href="04_mission2.html">미션 2</a><a href="05_mission3.html">미션 3</a><a href="06_extension.html">1주차 확장</a></nav>'
def table(tsv):
    lines=[line.split('\t') for line in tsv.strip().splitlines()]
    return '<table><thead><tr>'+''.join('<th>'+ESC(v)+'</th>' for v in lines[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+ESC(v)+'</td>' for v in row)+'</tr>' for row in lines[1:])+'</tbody></table>'
def page(title,body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+ESC(title)+'</title><style>'+CSS+'</style><main>'+NAV+'<div class="eyebrow">UMC WEEK 02 · SQL 실습 기록</div><h1>'+ESC(title)+'</h1><div class="meta">MySQL '+ESC(META['version'])+' · '+ESC(META['executed_at'])+' · 격리된 임시 MySQL 서버에서 실행</div>'+body+'<footer>실제 mysql CLI 출력을 HTML로 표시한 보고서입니다. DB 관리 도구 화면을 모사한 것이 아닙니다.<br>원본 TSV·실행 로그·verification.json을 results 폴더에 함께 보관합니다.</footer></main></html>'
body='<section><span class="badge">실행 및 결과 검증 PASS</span><h2>01_schema.sql → 02_seed.sql</h2><p>원본 SQL 두 파일을 수정 없이 순서대로 실행했습니다. 테이블 8개가 생성되었으며, INSERT 후 실제 행 수는 다음과 같습니다.</p>'+table(META['row_counts'])+'</section>'
body+='<div class="grid"><section><h2>검증 범위</h2><p>공통 SELECT 3개: 기대 결과 일치<br>1주차 확장 SELECT 1개: 별도 fixture에서 기대 결과 일치<br>추가 SELECT 4개: 태그 없음·좋아요 없음·없는 책·반납 완료 제외</p><div class="check">조회 전후 공통 테이블 행 수 및 원본 SQL 파일 해시가 동일합니다.</div></section><section><h2>재현 정보</h2><p>공통 DB: umc_week02_library<br>확장 DB: umc_week02_reward<br>실행 후 임시 MySQL 서버 정상 종료</p><p class="small">'+''.join(ESC(k)+': <code>'+v[:16]+'…</code><br>' for k,v in META['schema_and_seed_sha256'].items())+'</p><a href="00_setup.txt">원본 CREATE / INSERT 실행 로그</a></section></div>'
(OUT/'00_setup.html').write_text(page('테이블 생성 · 더미 데이터 실행 확인',body).replace('<main>','<main class="setup">'),encoding='utf-8')
DETAILS={
'03_mission1.sql':('미션 1 · 대여 가능한 문학 도서','book → category','book을 기준으로 category를 JOIN하여 분류 이름을 얻습니다. 문학·대여 가능 조건을 적용하고, 등록일이 없어 book_id 내림차순을 최신 등록순으로 가정해 최대 10권을 조회합니다.','달빛 도서관 1권만 조회되어 문학·대여 가능 조건과 일치합니다. 1행 데이터만으로 정렬 방향이나 10개 제한의 동작까지 관찰할 수는 없습니다.'),
'04_mission2.sql':('미션 2 · 사용자의 미반납 도서','rental → book','rental을 기준으로 book을 JOIN하여 책 제목을 얻습니다. 사용자 1과 returned_at IS NULL을 선택하고, 반납 예정일·대여 ID 오름차순으로 전체 목록을 조회합니다.','민서가 미반납한 겨울의 편지 1건과 대여일·반납 예정일이 조회되어 요구사항과 일치합니다.'),
'05_mission3.sql':('미션 3 · 책의 태그와 좋아요 여부','book → book_tag → tag / book → book_like','book을 기준으로 태그 연결과 특정 사용자의 좋아요를 LEFT JOIN합니다. 책 1을 선택하고 사용자 1 조건은 ON에 두며, 태그 ID 오름차순으로 태그당 한 행을 반환합니다.','달빛 도서관의 소설·추천 태그 2개와 민서의 좋아요 여부 1이 각 행에 조회되어 요구사항과 일치합니다.'),
'06_extension.sql':('확장 · 지역별 완료 미션 내역','member_mission → mission → store → region','member_mission을 기준으로 미션·가게·지역의 이름을 JOIN합니다. 회원 1·지역 1·완료 상태만 선택하고, 완료 시각·수행 ID 내림차순으로 최대 10건을 조회합니다.','회원 1의 안암동 완료 미션 2건만 최근 완료순으로 조회되고, 진행 중·다른 회원·다른 지역의 행은 제외되어 요구사항과 일치합니다.')}
for filename,(title,route,explanation,check) in DETAILS.items():
    sql=(ROOT/filename).read_text(encoding='utf-8')
    sql=sql[sql.index('SELECT'):sql.index(';')+1]
    tsv=META['queries'][filename]
    note='별도로 작성한 1주차 검증 데이터입니다. 공통 도서 더미 데이터가 아닙니다.' if filename=='06_extension.sql' else '제공된 02_seed.sql의 공통 더미 데이터에서 실행했습니다.'
    body='<section><span class="badge">실제 실행 결과 일치</span><p>'+note+'</p><strong>JOIN 경로</strong> <code>'+ESC(route)+'</code></section>'
    body+='<div class="grid"><section><h2>'+filename+'</h2><pre>'+ESC(sql)+'</pre></section><section><h2>실제 결과 · '+str(len(tsv.strip().splitlines())-1)+'행</h2>'+table(tsv)+'<div class="check">'+ESC(check)+'</div><p class="small">'+ESC(explanation)+'</p></section></div>'
    (OUT/(filename.removesuffix('.sql')+'.html')).write_text(page(title,body),encoding='utf-8')

# Draw code-native diagrams, with the actual FK paths used in the queries.
FONT='C:/Windows/Fonts/malgun.ttf'; BOLD='C:/Windows/Fonts/malgunbd.ttf'
def font(size,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)
im=Image.new('RGB',(2800,1700),'#F3F6FA'); d=ImageDraw.Draw(im)
def box(x,y,w,name,rows,color='#314D74'):
    h=85+47*len(rows)
    d.rounded_rectangle((x,y,x+w,y+h),radius=14,fill='white',outline='#C5D1DF',width=3)
    d.rectangle((x,y,x+w,y+72),fill=color)
    d.text((x+20,y+14),name,font=font(32,True),fill='white')
    for i,line in enumerate(rows):d.text((x+18,y+85+i*47),line,font=font(25),fill='#22334B')
    return h
def line(pts,color,left='1',right='0..N'):
    d.line(pts,fill=color,width=6)
    for p,q,label in [(pts[0],pts[1],left),(pts[-1],pts[-2],right)]:
        dx=q[0]-p[0];dy=q[1]-p[1];dist=(dx*dx+dy*dy)**.5
        offset=38 if len(label)>1 else 20
        x=p[0]+dx/dist*offset;y=p[1]+dy/dist*offset
        half=d.textlength(label,font=font(24,True))/2+5
        d.rectangle((x-half,y-20,x+half,y+22),fill='#F3F6FA')
        d.text((x,y),label,font=font(24,True),fill=color,anchor='mm')
d.text((70,40),'기준 ERD · 공통 실습 JOIN 경로',font=font(51,True),fill='#1B2940')
d.text((70,120),'파랑 = 미션 1   /   초록 = 미션 2   /   보라 = 미션 3   /   회색 = 그 외 기준 관계',font=font(28),fill='#50647F')
box(70,230,510,'users',['PK  user_id','nickname'])
box(820,230,610,'rental',['PK  rental_id','FK  user_id','FK  book_id','rented_at','due_at','returned_at ?'],'#16856A')
box(2110,230,610,'category',['PK  category_id','name'],'#376ED1')
box(1620,800,690,'book',['PK  book_id','FK  category_id','title','description ?','is_available'],'#376ED1')
box(820,800,610,'book_like',['PK/FK  user_id','PK/FK  book_id'],'#8754B4')
box(70,800,510,'notification',['PK  notification_id','FK  user_id','type'])
box(70,1320,510,'tag',['PK  tag_id','name'],'#8754B4')
box(820,1320,610,'book_tag',['PK/FK  book_id','PK/FK  tag_id'],'#8754B4')
line([(580,330),(820,330)],'#75879E')
line([(300,409),(300,800)],'#75879E')
line([(580,380),(680,380),(680,910),(820,910)],'#8754B4')
line([(1620,910),(1430,910)],'#8754B4')
line([(1950,800),(1950,450),(1430,450)],'#16856A')
line([(2415,409),(2415,650),(2180,650),(2180,800)],'#376ED1')
line([(1950,1120),(1950,1430),(1430,1430)],'#8754B4')
line([(580,1430),(820,1430)],'#8754B4')
d.text((70,1580),'PK = 기본키   FK = 외래키   ? = NULL 허용   1 = 정확히 하나   0..N = 0개 이상',font=font(27),fill='#50647F')
d.text((70,1630),'미션 2는 rental.user_id로 필터링하므로 users JOIN이 불필요합니다. 미션 3은 book_like.user_id를 ON 조건에 둡니다.',font=font(25),fill='#50647F')
im.save(OUT/'library-erd-join-paths.png')
im=Image.new('RGB',(2800,800),'#F3F6FA');d=ImageDraw.Draw(im)
d.text((70,40),'1주차 ERD 확장 · 완료 미션 화면 JOIN 경로',font=font(48,True),fill='#1B2940')
d.text((70,120),'기준: member_mission  /  회원 1 · 지역 1 · COMPLETED  /  completed_at DESC, id DESC  /  LIMIT 10',font=font(27),fill='#50647F')
box(70,260,610,'member_mission',['PK  id','FK  member_id / mission_id','status / completed_at','awarded_points'],'#087E8B')
box(800,260,530,'mission',['PK  id','FK  store_id','title'],'#087E8B')
box(1450,260,530,'store',['PK  id','FK  region_id','name'],'#087E8B')
box(2100,260,610,'region',['PK  id','name'],'#087E8B')
line([(680,370),(800,370)],'#087E8B','0..N','1')
line([(1330,370),(1450,370)],'#087E8B','0..N','1')
line([(1980,370),(2100,370)],'#087E8B','0..N','1')
d.text((70,650),'필터는 ID로, 화면 표시는 이름으로 처리합니다. 각 JOIN은 N:1이므로 수행 내역 한 행이 여러 행으로 늘어나지 않습니다.',font=font(28),fill='#50647F')
d.text((70,710),'조회에 사용하는 주요 컬럼과 관계만 표시했습니다. 전체 컬럼·관계는 week01/erd의 원본 ERD를 참고합니다.',font=font(26),fill='#50647F')
im.save(OUT/'extension-erd-join-path.png')

record=['# 2주차 미션 기록 — 온라인 도서 대여 조회와 1주차 ERD 확장','',
'''## 실행 확인

제공된 `01_schema.sql`과 `02_seed.sql`을 수정 없이 MySQL에서 실행한 뒤 공통 SELECT 3개를 조회했다. 기존 서비스 DB와 분리된 임시 로컬 MySQL 서버를 사용했으며, 검증을 마친 뒤 종료했다. 확장 쿼리는 1주차 리워드 ERD를 재현한 별도 DB와 별도로 작성한 검증 데이터를 사용했다.

`results/*.png`는 **실제 mysql CLI 출력을 HTML 보고서로 표시하고 브라우저에서 캡처한 이미지**다. Workbench 실행 화면은 아니며, 원본 출력도 TSV 및 로그로 함께 제공한다.
''',
f'- 실행 환경: MySQL {META["version"]}',f'- 실행 시각: {META["executed_at"]}',
'- 원본 실행 로그: [00_setup.txt](results/00_setup.txt)',
'- 검증 결과·원본 파일 해시: [verification.json](results/verification.json)',
'','![테이블 생성 및 더미 데이터 실행 확인](results/00_setup.png)','',
'''## ERD와 JOIN 경로

![기준 ERD와 JOIN 경로](results/library-erd-join-paths.png)

파랑은 미션 1, 초록은 미션 2, 보라는 미션 3에서 사용하는 관계를 나타낸다. 보라색 users–book_like 관계는 좋아요 소유자의 의미를 보여주며 실제 미션 3 SQL은 users를 JOIN하지 않는다. 관계선의 1은 정확히 하나, 0..N은 0개 이상이다.

공통 관계는 users 1:N rental, book 1:N rental, category 1:N book, book N:M tag(book_tag), users N:M book(book_like), users 1:N notification이다. 연결 테이블의 복합 PK가 같은 책·태그 및 같은 사용자·책의 중복 연결을 방지한다.

## 조회 정책

- 특정 사용자: `user_id = 1`(민서). 특정 책: `book_id = 1`(달빛 도서관).
- 최신순: book에는 등록 시각이 없으므로 **book_id가 클수록 최근 등록된 책**이라고 가정한다. 실제 등록 시각순이 필요한 시스템에서는 created_at 같은 컬럼을 별도로 설계해야 한다.
- 미반납: `returned_at IS NULL`. 반납 예정일이 지났더라도 아직 반납하지 않았으면 포함한다.
- 미션 3: 태그당 한 행. 좋아요는 1/0으로 표시한다. 태그가 없으면 NULL 태그 행 하나를, 책 자체가 없으면 0행을 반환한다.
- `LIMIT 10`은 최대 10개이므로 조건에 맞는 행이 1개뿐이면 1개만 나온다.
''']
requirements={
 '03_mission1.sql':'문학 카테고리의 대여 가능한 도서를 최신순으로 최대 10개 조회하고, 책 제목·설명·카테고리 이름을 표시한다.',
 '04_mission2.sql':'사용자 1이 아직 반납하지 않은 책을 반납 예정일이 빠른 순으로 조회하고, 책 제목·대여일·반납 예정일을 표시한다.',
 '05_mission3.sql':'책 1의 태그 목록과 사용자 1의 좋아요 여부를 조회한다.',
 '06_extension.sql':'회원 1이 지역 1에서 완료한 미션을 최근 완료순으로 최대 10개 조회하고, 미션명·가게명·지역명·완료 시각·미션 획득 포인트를 표시한다.'}
for filename,(title,route,explanation,check) in DETAILS.items():
    sql=(ROOT/filename).read_text(encoding='utf-8'); sql=sql[sql.index('SELECT'):sql.index(';')+1]
    # Preserve the three explanation sentences stored below each submitted query.
    source=(ROOT/filename).read_text(encoding='utf-8')
    explanation=' '.join(line.removeprefix('-- ') for line in source[source.index(';')+1:].strip().splitlines())
    stem=filename.removesuffix('.sql')
    record += [f'## {title}','',f'**요구사항:** {requirements[filename]}','',f'파일: [{filename}]({filename})','',
        '```sql',sql,'```','',explanation,'',f'**JOIN 경로:** `{route}`','']
    if filename=='06_extension.sql':
        record += ['![확장 ERD JOIN 경로](results/extension-erd-join-path.png)','',
                   '위 그림은 조회에 사용하는 1주차 테이블과 주요 컬럼만 표시했다. [1주차 전체 ERD](../week01/erd/reward-service-erd.png) 및 [컬럼 정의](../week01/erd/schema.md)와 동일한 관계다. 확장 결과는 공통 도서 더미 데이터가 아닌 별도 검증 데이터에서 실행했다.','',
                   '`awarded_points`는 해당 미션의 보상이며 지역 10회 보너스나 전체 잔액이 아니다. 이미 완료한 과거 내역이므로 가게나 미션의 현재 활성 상태를 추가 필터로 사용하지 않는다.','']
    record += [f'![{title} 실행 결과](results/{stem}.png)','',f'**한 문장 검증:** {check.split(" 1행 데이터만으로")[0]}','',f'원본 결과: [{stem}.tsv](results/{stem}.tsv)','']
record += ['''## 질문과 답변

### 어떤 요구사항에서 어떤 테이블을 기준으로 시작했나요?

| 요구사항 | 기준 테이블 | 선택 이유 |
|---|---|---|
| 문학·대여 가능 도서 | book | 조회할 대상과 대여 가능 상태가 책에 있다. |
| 특정 사용자의 미반납 목록 | rental | 사용자·미반납 여부·대여일·반납 예정일이 대여 내역에 있다. |
| 특정 책의 태그·좋아요 | book | 태그나 좋아요가 없어도 책은 결과에 남겨야 한다. |
| 특정 회원의 지역별 완료 미션 | member_mission | 회원별 완료 상태·완료 시각·확정 포인트가 수행 내역에 있다. |

### JOIN이 필요한 이유를 ERD의 관계로 설명할 수 있나요?

미션 1은 book.category_id가 category.category_id를 참조하는 N:1 관계를 이용해 분류 이름을 가져온다. 미션 2는 rental.book_id가 book.book_id를 참조하는 N:1 관계를 이용해 제목을 가져오며, 사용자 ID는 rental에 있으므로 users를 추가로 JOIN하지 않는다.

미션 3은 책과 태그의 N:M 관계를 book_tag를 거쳐 조회하고, 사용자와 책의 N:M 관계를 book_like에서 확인한다. 사용자 조건을 ON에 적용하면 복합 PK(user_id, book_id)에 의해 좋아요 행은 최대 1개만 연결되므로 태그 행이 불필요하게 늘어나지 않는다. 태그 2개 때문에 같은 책이 2행 나오는 것은 의도한 결과다.

확장 쿼리는 member_mission → mission → store → region의 N:1 경로를 따라 화면에 필요한 이름을 가져온다. 각 수행 내역이 미션·가게·지역 하나씩에 연결되므로 JOIN 후에도 수행 내역당 한 행을 유지한다.

### 더미 데이터 결과가 예상과 달랐을 때 어떤 조건 또는 관계를 먼저 확인했나요?

이번 실제 실행에서는 예상 결과와 불일치한 사례는 없었다. 대신 다음 경계 사례를 공통 데이터를 수정하지 않는 SELECT로 추가 확인했다.

| 확인 사례 | 실제 결과 | 우선 확인할 조건·관계 |
|---|---|---|
| 태그·좋아요가 없는 책 2 | 겨울의 편지 / NULL / 0 | INNER JOIN으로 책을 제거하지 않았는지 확인한다. |
| 책 1을 좋아요하지 않은 사용자 2 | 소설·추천 각각 is_liked=0 | 사용자 조건이 WHERE가 아닌 LEFT JOIN의 ON에 있는지 확인한다. |
| 존재하지 않는 책 999 | 0행 | WHERE에 전달한 책 ID와 실제 원본 행을 확인한다. |
| 이미 반납한 사용자 2의 대여 | 0행 | `returned_at IS NULL`인지 확인한다. `= NULL`을 쓰지 않는다. |

미션 1의 겨울의 편지는 문학이지만 is_available=FALSE여서 제외되고, 우주를 읽는 법은 대여 가능하지만 과학이어서 제외된다. 미션 2의 겨울의 편지는 반납 예정일이 지났지만 returned_at이 NULL이므로 계속 포함되는 것이 맞다. 결과 행이 과도하게 늘어나면 JOIN의 PK–FK 연결과 N:M 연결 테이블을 먼저 확인한다.

## 검증 범위와 한계

- 원본 스키마·더미 데이터 파일의 해시는 실행 전후 동일하다. 공통 실습 및 추가 확인은 SELECT만 사용했으며 공통 테이블 행 수도 동일하다.
- 공통 미션 1·2는 결과가 1행이어서 정렬 순서를 여러 행에서 관찰할 수 없다. 미션 1의 10개 제한도 경계 데이터로 검증하지 않았으며 SQL의 ORDER BY·LIMIT과 실행 성공을 확인한 범위다.
- 확장은 두 완료 시각의 내림차순 및 진행 중·다른 회원·다른 지역 제외를 확인했다. 동률 정렬과 10개 제한의 경계 사례는 별도로 실행하지 않았다.
- validation/extension_schema.sql은 1주차의 컬럼·PK·FK·UNIQUE를 재현한 조회 검증용 DDL이다. 운영용 CHECK·인증·포인트 지급 로직 구현물이 아니다.

## 실행 순서와 제출 파일

공통 실습은 새로 만든 빈 MySQL 실습 DB를 선택한 후 `01_schema.sql → 02_seed.sql → 03_mission1.sql → 04_mission2.sql → 05_mission3.sql` 순서로 실행한다. 06_extension.sql은 도서 DB에서 실행하지 않는다. 별도 빈 리워드 실습 DB에서 `validation/extension_schema.sql → validation/extension_seed.sql → 06_extension.sql` 순서로 실행한다.

| 제출 항목 | 파일 |
|---|---|
| 스키마·더미 데이터 | 01_schema.sql, 02_seed.sql |
| 공통 조회 3개 | 03_mission1.sql, 04_mission2.sql, 05_mission3.sql |
| 1주차 확장 조회 | 06_extension.sql |
| 미션 기록·설명·질문 답변 | README.md(현재 문서) |
| 실행 확인 캡처 | results/00_setup.png |
| 조회 결과 캡처 4개 | results/03_mission1.png, 04_mission2.png, 05_mission3.png, 06_extension.png |
| JOIN 경로가 표시된 ERD | results/library-erd-join-paths.png, results/extension-erd-join-path.png |
| 원본 실행 증거 | results/00_setup.txt, results/*.tsv, results/verification.json |

자동 검증을 재현하려면 Python으로 `validation/verify_mysql.py`를 실행한다. 설치된 MySQL 바이너리 경로가 다르면 MYSQL_BIN 환경변수로 지정할 수 있다. 이 스크립트는 새로운 임시 서버를 생성·검증·종료하며 기존 MySQL 서비스에 연결하지 않는다. 보고서와 ERD 생성은 Pillow가 설치된 Python으로 `validation/build_report.py`를 실행한다. 브라우저 캡처 PNG는 결과 HTML에서 별도로 캡처한 파일이므로 재실행 결과가 바뀌면 다시 캡처해야 한다.
''']
(ROOT/'README.md').write_text('\n'.join(record)+'\n',encoding='utf-8')
print('Created submission README, 5 result HTML pages and 2 ERD PNGs from verified outputs.')
