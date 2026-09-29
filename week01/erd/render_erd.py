"""Generate submission ERD PNGs, Mermaid source and data dictionary. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
# field, logical type, key, nullable, explanation
TABLES = {
    'member': ('회원', [
        ('id','bigint','PK',False,'회원 식별자'),
        ('name','varchar(50)','',False,'가입 시 입력하는 이름'),
        ('nickname','varchar(50)','',False,'리뷰 및 마이페이지 표시 이름'),
        ('email','varchar(255)','',True,'연락용 이메일. 소셜 계정 식별키로 사용하지 않음'),
        ('phone','varchar(20)','',True,'선택 연락처'),
        ('gender','varchar(20)','',False,'MALE / FEMALE / UNSPECIFIED'),
        ('birth_date','date','',False,'생년월일'),
        ('address','varchar(255)','',False,'가입 화면의 주소'),
        ('address_detail','varchar(255)','',True,'상세 주소'),
        ('profile_image_url','varchar(500)','',True,'프로필 이미지'),
        ('status','varchar(20)','',False,'ACTIVE / WITHDRAWN'),
        ('created_at','datetime','',False,'가입 시각'),
        ('updated_at','datetime','',False,'최종 수정 시각'),
        ('withdrawn_at','datetime','',True,'탈퇴 시각'),
    ]),
    'social_account': ('소셜 로그인 연결', [
        ('id','bigint','PK',False,'소셜 계정 연결 식별자'),
        ('member_id','bigint','FK',False,'member.id'),
        ('provider','varchar(20)','',False,'KAKAO / NAVER / APPLE / GOOGLE'),
        ('provider_user_id','varchar(255)','',False,'소셜 제공자가 발급하는 사용자 식별자'),
        ('created_at','datetime','',False,'연결 시각'),
    ]),
    'food_category': ('음식 종류', [
        ('id','bigint','PK',False,'음식 카테고리 식별자'),
        ('name','varchar(50)','UK',False,'한식, 일식, 중식, 디저트 등'),
    ]),
    'member_food_category': ('회원 음식 선호도', [
        ('member_id','bigint','PK,FK',False,'member.id'),
        ('food_category_id','bigint','PK,FK',False,'food_category.id'),
    ]),
    'terms': ('약관 버전', [
        ('id','bigint','PK',False,'약관 버전 식별자'),
        ('code','varchar(50)','',False,'SERVICE / PRIVACY / LOCATION / MARKETING 등'),
        ('version','varchar(30)','',False,'약관 버전'),
        ('title','varchar(100)','',False,'약관 제목'),
        ('content','text','',False,'해당 버전의 약관 내용'),
        ('is_required','boolean','',False,'필수 동의 여부'),
        ('effective_at','datetime','',False,'시행 시각'),
    ]),
    'member_agreement': ('회원 약관 동의', [
        ('member_id','bigint','PK,FK',False,'member.id'),
        ('terms_id','bigint','PK,FK',False,'terms.id'),
        ('agreed','boolean','',False,'해당 버전의 현재 동의 여부'),
        ('agreed_at','datetime','',True,'동의 시각. 동의한 경우 필수'),
        ('revoked_at','datetime','',True,'동의 철회 시각'),
    ]),
    'region': ('서비스 지역', [
        ('id','bigint','PK',False,'보상 집계 단위인 지역 식별자'),
        ('code','varchar(30)','UK',False,'지역 고유 코드'),
        ('name','varchar(100)','',False,'안암동 등 표시명. 동명 지역 허용'),
    ]),
    'store': ('가게', [
        ('id','bigint','PK',False,'가게 식별자'),
        ('region_id','bigint','FK',False,'region.id'),
        ('food_category_id','bigint','FK',False,'food_category.id. 대표 카테고리 1개 가정'),
        ('name','varchar(100)','',False,'가게명'),
        ('address','varchar(255)','',False,'가게 주소'),
        ('description','text','',True,'가게 소개'),
        ('phone','varchar(20)','',True,'연락처'),
        ('image_url','varchar(500)','',True,'대표 사진'),
        ('status','varchar(20)','',False,'OPEN / CLOSED'),
    ]),
    'mission': ('미션 정의', [
        ('id','bigint','PK',False,'미션 식별자'),
        ('store_id','bigint','FK',False,'store.id'),
        ('title','varchar(100)','',False,'미션 제목'),
        ('description','text','',False,'미션 조건 설명'),
        ('min_spend','decimal(12,0)','',False,'최소 결제 금액. 단순 방문이면 0'),
        ('reward_type','varchar(20)','',False,'FIXED / RATE'),
        ('reward_value','decimal(12,2)','',False,'FIXED이면 포인트, RATE이면 백분율. 5는 5%'),
        ('starts_at','datetime','',False,'미션 시작 시각'),
        ('ends_at','datetime','',False,'미션 종료 시각'),
        ('status','varchar(20)','',False,'ACTIVE / INACTIVE'),
    ]),
    'member_mission': ('회원별 수행 내역', [
        ('id','bigint','PK',False,'수행 내역 식별자'),
        ('member_id','bigint','FK',False,'member.id'),
        ('mission_id','bigint','FK',False,'mission.id'),
        ('status','varchar(20)','',False,'IN_PROGRESS / PENDING / COMPLETED / CANCELLED / EXPIRED'),
        ('accepted_at','datetime','',False,'미션 도전 시각'),
        ('completed_at','datetime','',True,'완료 시각. COMPLETED일 때 필수'),
        ('verification_code_hash','varchar(255)','',True,'성공 요청 시 생성한 인증번호의 해시'),
        ('code_expires_at','datetime','',True,'인증번호 만료 시각'),
        ('paid_amount','decimal(12,0)','',True,'인증한 결제 금액. 완료 시 필수, 단순 방문은 0'),
        ('awarded_points','int','',True,'완료 당시 확정한 미션 보상. 미완료 NULL, 무보상 0'),
        ('updated_at','datetime','',False,'상태 최종 변경 시각'),
    ]),
    'region_reward': ('지역 10회 달성 보상', [
        ('id','bigint','PK',False,'지역 보상 식별자'),
        ('member_id','bigint','FK',False,'member.id'),
        ('region_id','bigint','FK',False,'region.id'),
        ('cycle_no','int','',False,'1=10회, 2=20회, 3=30회 달성'),
        ('points','int','',False,'지급 포인트. 현재 정책은 1000 고정'),
        ('awarded_at','datetime','',False,'지급 시각'),
    ]),
    'review': ('완료 미션 리뷰', [
        ('id','bigint','PK',False,'리뷰 식별자'),
        ('member_mission_id','bigint','FK,UK',False,'member_mission.id. 완료 내역당 리뷰 최대 1개'),
        ('rating','decimal(2,1)','',False,'0.5~5.0, 0.5 단위 가정'),
        ('content','text','',True,'텍스트 리뷰. 별점만 등록 가능하다고 가정'),
        ('created_at','datetime','',False,'작성 시각'),
        ('updated_at','datetime','',False,'최종 수정 시각'),
    ]),
    'review_image': ('리뷰 사진', [
        ('id','bigint','PK',False,'리뷰 사진 식별자'),
        ('review_id','bigint','FK',False,'review.id'),
        ('image_url','varchar(500)','',False,'사진 URL'),
        ('sort_order','smallint','',False,'1~3. 리뷰당 최대 3장'),
    ]),
}
UNIQUE = {
    'social_account': 'UNIQUE(provider, provider_user_id)',
    'terms': 'UNIQUE(code, version)',
    'member_mission': 'UNIQUE(member_id, mission_id)',
    'region_reward': 'UNIQUE(member_id, region_id, cycle_no)',
    'review_image': 'UNIQUE(review_id, sort_order)',
}
RELATIONS = [
    ('member','social_account','o{','로그인연결',False),
    ('member','member_food_category','o{','선호선택',True),
    ('food_category','member_food_category','o{','선호분류',True),
    ('member','member_agreement','o{','약관동의',True),
    ('terms','member_agreement','o{','동의대상',True),
    ('region','store','o{','지역소속',False),
    ('food_category','store','o{','가게분류',False),
    ('store','mission','o{','미션제공',False),
    ('member','member_mission','o{','미션도전',False),
    ('mission','member_mission','o{','수행내역',False),
    ('member','region_reward','o{','보상수령',False),
    ('region','region_reward','o{','지역보상',False),
    ('member_mission','review','o|','완료후리뷰',False),
    ('review','review_image','o{','사진첨부',False),
]
FONT = 'C:/Windows/Fonts/malgun.ttf'
BOLD = 'C:/Windows/Fonts/malgunbd.ttf'
def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)

WIDTH = 3000
INK = '#1B2940'
MUTED = '#596A80'
BG = '#F3F6FA'
class Diagram:
    def __init__(self, height, number, title, subtitle, color):
        self.im = Image.new('RGB',(WIDTH,height),BG)
        self.d = ImageDraw.Draw(self.im)
        self.color = color
        self.boxes = {}
        self.d.text((100,45),f'{number}  {title}',font=font(52,True),fill=INK)
        self.d.text((100,123),subtitle,font=font(27),fill=MUTED)
        self.d.text((100,height-90),'PK 기본키   FK 외래키   UK 단일 UNIQUE   ? NULL 허용   |   1 = 정확히 하나 / 0..N = 0개 이상 / 0..1 = 최대 하나',font=font(25),fill=MUTED)
        self.d.text((100,height-49),'실선: 부모 키가 자식 PK에 포함되는 식별 관계  ·  점선: 비식별 관계  ·  [참조]는 다른 영역에 나온 동일 테이블',font=font(23),fill=MUTED)
    def card(self, name,x,y,ref=False):
        label, rows = TABLES[name]
        if ref: rows = rows[:1]
        w=850; h=90+44*len(rows)+(48 if name in UNIQUE and not ref else 24)
        self.boxes[name]=(x,y,w,h)
        d=self.d
        d.rounded_rectangle((x,y,x+w,y+h),radius=18,fill='white',outline='#CBD5E1',width=2)
        d.rounded_rectangle((x,y,x+w,y+84),radius=18,fill=self.color)
        d.rectangle((x,y+45,x+w,y+84),fill=self.color)
        d.text((x+22,y+10),name+('  [참조]' if ref else ''),font=font(31,True),fill='white')
        d.text((x+22,y+49),label,font=font(22),fill='#E7EDF7')
        for i,(field,typ,key,nullable,desc) in enumerate(rows):
            yy=y+95+i*44
            if i%2==1: d.rectangle((x+2,yy-5,x+w-2,yy+38),fill='#F5F8FC')
            d.text((x+15,yy),key.replace(',','/'),font=font(18,True),fill=self.color)
            d.text((x+104,yy-1),field,font=font(27),fill=INK)
            dtype=typ+(' ?' if nullable else '')
            d.text((x+w-18,yy+2),dtype,font=font(22),fill=MUTED,anchor='ra')
        if name in UNIQUE and not ref:
            d.text((x+20,y+h-37),UNIQUE[name],font=font(21,True),fill=self.color)
        return h
    def edge(self, pts, end='0..N', identifying=False):
        d=self.d; color='#667B96'
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            if identifying:
                d.line((x1,y1,x2,y2),fill=color,width=4)
            else:
                length=((x2-x1)**2+(y2-y1)**2)**0.5
                for start in range(0,int(length),17):
                    t1=start/length; t2=min(start+10,length)/length
                    d.line((x1+(x2-x1)*t1,y1+(y2-y1)*t1,x1+(x2-x1)*t2,y1+(y2-y1)*t2),fill=color,width=4)
        # Small cardinality badges next to each endpoint, on the connection line.
        for p,q,text in [(pts[0],pts[1],'1'),(pts[-1],pts[-2],end)]:
            dx=q[0]-p[0]; dy=q[1]-p[1]; length=(dx*dx+dy*dy)**0.5
            xx=p[0]+dx/length*39; yy=p[1]+dy/length*39
            box=d.textbbox((0,0),text,font=font(22,True)); tw=box[2]-box[0]
            d.rounded_rectangle((xx-tw/2-6,yy-16,xx+tw/2+6,yy+18),radius=4,fill=BG)
            d.text((xx,yy),text,font=font(22,True),fill=INK,anchor='mm')
    def save(self,name):
        self.im.save(OUT/name)

def main():
    a=Diagram(1870,'01','회원가입 · 소셜 로그인 · 음식 선호도','회원의 프로필, 외부 로그인 계정, 음식 선택 및 약관 동의를 분리합니다.','#355C9A')
    a.card('member',100,230)
    a.card('social_account',1100,230)
    a.card('terms',2100,230)
    a.card('member_food_category',100,1290)
    a.card('food_category',1100,1290)
    a.card('member_agreement',2100,1290)
    a.edge([(950,335),(1100,335)])
    a.edge([(500,960),(500,1290)],identifying=True)
    a.edge([(1100,1400),(950,1400)],identifying=True)
    a.edge([(950,800),(1020,800),(1020,1140),(2010,1140),(2010,1400),(2100,1400)],identifying=True)
    a.edge([(2525,676),(2525,1290)],identifying=True)
    a.save('01-members.png')

    b=Diagram(1900,'02','지역 · 가게 · 미션 · 지역 달성 보상','미션 조건과 회원별 수행 상태를 분리하고, 지역별 10회 달성 보상의 중복 지급을 막습니다.','#087E8B')
    b.card('member',100,230,True)
    b.card('member_mission',1100,230)
    mh=b.card('mission',2100,230)
    b.card('region_reward',100,1100)
    b.card('region',1100,1100)
    b.card('store',2100,1100)
    b.card('food_category',1100,1550,True)
    b.edge([(950,335),(1100,335)])
    b.edge([(2100,335),(1950,335)])
    b.edge([(500,388),(500,1100)])
    b.edge([(1100,1210),(950,1210)])
    b.edge([(1950,1210),(2100,1210)])
    b.edge([(2525,1100),(2525,230+mh)])
    b.edge([(1950,1650),(2020,1650),(2020,1490),(2100,1490)])
    b.d.rounded_rectangle((1100,1410,1950,1500),radius=12,fill='#E2F1F2')
    b.d.text((1123,1422),'10 · 20 · 30회 달성마다 1,000P (설계 가정)',font=font(27,True),fill='#086B75')
    b.d.text((1123,1463),'UNIQUE(member_id, region_id, cycle_no)',font=font(22),fill='#086B75')
    b.save('02-missions.png')

    c=Diagram(850,'03','완료한 미션 · 리뷰 · 리뷰 사진','완료 내역당 리뷰 최대 1개, 리뷰당 사진 최대 3장. 작성자와 가게는 수행 내역에서 조회합니다.','#7853A2')
    c.card('member_mission',100,230,True)
    c.card('review',1100,230)
    c.card('review_image',2100,230)
    c.edge([(950,335),(1100,335)],end='0..1')
    c.edge([(1950,335),(2100,335)])
    c.d.text((2130,605),'사진 3장 제한: CHECK(sort_order BETWEEN 1 AND 3)',font=font(24),fill=MUTED)
    c.save('03-reviews.png')
    full=Image.new('RGB',(WIDTH,a.im.height+b.im.height+c.im.height),'white')
    offset=0
    for panel in (a.im,b.im,c.im):
        full.paste(panel,(0,offset)); offset+=panel.height
    full.save(OUT/'reward-service-erd.png')

    # Use camelCase Mermaid IDs and preserve physical table names as aliases.
    ids={name: name.split('_')[0]+''.join(p.title() for p in name.split('_')[1:]) for name in TABLES}
    lines=['erDiagram','    direction LR']
    for parent,child,card,label,identifying in RELATIONS:
        lines.append(f'    {ids[parent]} ||{"--" if identifying else ".."}{card} {ids[child]} : {label}')
    for name,(label,fields) in TABLES.items():
        lines.append(f'    {ids[name]}["{name}"] {{')
        for field,typ,key,nullable,desc in fields:
            mtype=typ.split('(')[0]
            keys=(' '+key.replace(',',', ')) if key else ''
            comment=' "nullable"' if nullable else ''
            lines.append(f'        {mtype} {field}{keys}{comment}')
        lines.append('    }')
    (OUT/'reward-service.mmd').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    doc=['# 테이블 상세 정의','',
         '총 13개 테이블의 논리 설계입니다. `bigint` 단일 PK는 자동 생성하며, 복합 PK는 연결 대상의 키를 사용합니다. 타입은 MySQL 계열 표기이며 실행용 DDL은 아닙니다.', '',
         '`NULL`은 허용 여부입니다. 상태값, 금액 범위, 완료 조건 및 트랜잭션 규칙은 [설계 설명](README.md)을 함께 참고합니다.','']
    for name,(label,fields) in TABLES.items():
        doc += [f'## {name} — {label}','','| 컬럼 | 타입 | 키 | NULL | 설명 |','|---|---|---|---|---|']
        for field,typ,key,nullable,desc in fields:
            doc.append(f'| `{field}` | `{typ}` | {key or "—"} | {"허용" if nullable else "불가"} | {desc} |')
        doc.append('')
        if name in UNIQUE: doc += [f'추가 제약: `{UNIQUE[name]}`.','']
    (OUT/'schema.md').write_text('\n'.join(doc),encoding='utf-8')
    print(f'Generated 4 PNGs, Mermaid source and schema.md in {OUT}')

if __name__ == '__main__':
    main()
