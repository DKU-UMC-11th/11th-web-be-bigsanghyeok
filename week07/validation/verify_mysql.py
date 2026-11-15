"""Verify week07 JWT authentication and rating ownership against isolated MySQL."""
from pathlib import Path
import argparse
import base64
import secrets
import datetime
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
BIN = Path(os.environ.get('MYSQL_BIN', 'C:/Program Files/MySQL/MySQL Server 26.7/bin'))
JAVA = str(Path(os.environ['JAVA_HOME']) / 'bin/java.exe') if os.environ.get('JAVA_HOME') else shutil.which('java')
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', help='Keep the isolated API running for Postman screenshots.')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    port = int(os.environ.get('SERVER_PORT', '18087'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))  # Never send test writes to an existing server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        db_port = sock.getsockname()[1]
    data = Path(tempfile.mkdtemp(prefix='umc_week07_mysql_'))
    subprocess.run([str(BIN / 'mysqld.exe'), '--no-defaults', '--initialize-insecure',
        f'--datadir={data}', '--console'], capture_output=True, check=True, timeout=120, creationflags=FLAGS)
    db_log = (data / 'server.log').open('wb')
    app_log = (RESULTS / 'server.log').open('wb')
    db = subprocess.Popen([str(BIN / 'mysqld.exe'), '--no-defaults', f'--datadir={data}',
        f'--port={db_port}', '--bind-address=127.0.0.1', '--mysqlx=OFF', '--skip-log-bin', '--console'],
        stdout=db_log, stderr=db_log, creationflags=FLAGS)
    app = None
    base = [str(BIN / 'mysql.exe'), '--no-defaults', '--no-login-paths', '--protocol=TCP',
        '--host=127.0.0.1', f'--port={db_port}', '--user=root', '--default-character-set=utf8mb4', '--batch', '--raw']

    def query(sql, database=None):
        result = subprocess.run(base + ([f'--database={database}'] if database else []),
            input=sql.encode('utf-8'), capture_output=True, timeout=30, creationflags=FLAGS)
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
        return result.stdout.decode('utf-8').replace('\r\n', '\n')

    cases = []

    def request(name, method, path, body=None, status=200, token=None, raw_body=None, authorization=None):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        if raw_body is not None:
            payload = raw_body.encode()
        headers = {'Content-Type':'application/json'} if payload is not None else {}
        if token is not None:
            headers['Authorization'] = 'Bearer ' + token
        if authorization is not None:
            headers['Authorization'] = authorization
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path, method=method, data=payload,
            headers=headers)
        try:
            response = urllib.request.urlopen(req,timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read().decode('utf-8')
            value = json.loads(raw) if raw else None
            record = {'name':name,'method':method,'url':req.full_url,'request_body':body if raw_body is None else raw_body,
                'authenticated':token is not None,'status':response.status,'response':value,'body_bytes':len(raw.encode())}
        cases.append(record)
        if response.status != status:
            (RESULTS/'failed-attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        assert response.status == status, record
        if status not in (404,405) or isinstance(value,dict) and 'isSuccess' in value:
            if isinstance(value,list) or path.startswith(('/members/nickname/','/members/email/')):
                return value
            assert set(value) == {'isSuccess','code','message','result'}, record
            assert value['isSuccess'] is (status < 400), record
            if status >= 400:
                assert value['result'] is None and value['message'], record
        if status == 204:
            assert raw == '', record
        return value

    try:
        for _ in range(160):
            if db.poll() is not None:
                raise RuntimeError((data / 'server.log').read_text(errors='replace'))
            try:
                version = query('SELECT VERSION();').splitlines()[1]
                break
            except RuntimeError:
                time.sleep(.25)
        else:
            raise RuntimeError('MySQL startup timed out')
        fixtures = [ROOT / 'sql/01_schema.sql', ROOT / 'sql/02_seed.sql']
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        query('CREATE DATABASE umc_movie CHARACTER SET utf8mb4;')
        for fixture in fixtures:
            query(fixture.read_text(encoding='utf-8'), 'umc_movie')
        env = dict(os.environ, DB_URL=f'jdbc:mysql://127.0.0.1:{db_port}/umc_movie?serverTimezone=Asia/Seoul&characterEncoding=UTF-8',
            DB_USER='root', DB_PASSWORD='', SERVER_PORT=str(port), SERVER_ADDRESS='127.0.0.1', CORS_ENABLED='true', JWT_SECRET=secrets.token_urlsafe(48), JWT_ACCESS_EXPIRATION='3600')
        app = subprocess.Popen([JAVA, '-jar', str(ROOT / 'build/libs/movie-auth-api-0.0.1-SNAPSHOT.jar')],
            env=env, stdout=app_log, stderr=app_log, creationflags=FLAGS)
        for _ in range(160):
            if app.poll() is not None:
                raise RuntimeError((RESULTS / 'server.log').read_text(errors='replace'))
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/members/1/ratings', timeout=2):
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(.5)
        else:
            raise RuntimeError('Spring startup timed out')

        def fail(name, method, path, body, status, code, token=None, **kwargs):
            value = request(name, method, path, body, status, token=token, **kwargs)
            assert value['code'] == code, value
            return value

        def signup(email, nickname):
            return {'email':email, 'password':'Movie123!', 'nickname':nickname}

        a = request('시나리오 1 A 회원가입', 'POST', '/members', signup('a@umc.com','영화팬A'),201)['result']['memberId']
        b = request('시나리오 1 B 회원가입', 'POST', '/members', signup('b@umc.com','영화팬B'),201)['result']['memberId']
        def login(email, password='Movie123!'):
            return {'email':email,'password':password}
        token_a = request('시나리오 2 A 로그인', 'POST', '/auth/login', login('a@umc.com'))['result']['accessToken']
        token_b = request('시나리오 2 B 로그인', 'POST', '/auth/login', login('b@umc.com'))['result']['accessToken']
        payload = json.loads(base64.urlsafe_b64decode(token_a.split('.')[1]+'=='))
        assert set(payload) == {'sub','email','iat','exp'} and payload['sub']==str(a)
        assert payload['email']=='a@umc.com' and payload['exp']-payload['iat']==3600
        assert 'password' not in json.dumps(payload)
        stored = query(f'SELECT password FROM member WHERE member_id={a};','umc_movie').splitlines()[1]
        other = query(f'SELECT password FROM member WHERE member_id={b};','umc_movie').splitlines()[1]
        assert stored.startswith('$2a$10$') and len(stored)==60 and stored!=other

        body = {'movieId':27205,'score':4,'comment':'토큰으로 등록한 평점'}
        rating = request('시나리오 3 본인 평점 등록', 'POST','/ratings',body,201,token=token_a)['result']['ratingId']
        assert query(f'SELECT member_id FROM rating WHERE rating_id={rating};','umc_movie').splitlines()[1]==str(a)
        count_before = query('SELECT COUNT(*) FROM rating;','umc_movie')
        fail('시나리오 4 중복 평점', 'POST','/ratings',body,409,'RATING409_1',token_a)
        assert query('SELECT COUNT(*) FROM rating;','umc_movie')==count_before
        update = {'score':5,'comment':'내 토큰으로 수정 완료'}
        time.sleep(1.1)  # DATETIME stores whole seconds; distinguish creation from update.
        changed = request('시나리오 5 본인 수정', 'PATCH',f'/ratings/{rating}',update,token=token_a)['result']
        assert changed['score']==5 and changed['comment']==update['comment']
        assert datetime.datetime.fromisoformat(changed['updatedAt']) > datetime.datetime.fromisoformat(changed['createdAt'])
        fail('시나리오 6 남의 평점 수정', 'PATCH',f'/ratings/{rating}',update,403,'RATING403_1',token_b)
        assert query(f'SELECT score, comment FROM rating WHERE rating_id={rating};','umc_movie').splitlines()[1]=='5\t'+update['comment']
        fail('시나리오 7 토큰 없이 수정', 'PATCH',f'/ratings/{rating}',update,401,'AUTH401_2')
        fail('시나리오 8 없는 평점 삭제', 'DELETE','/ratings/99999',None,404,'RATING404_1',token_a)
        removed = request('시나리오 9 본인 삭제', 'DELETE',f'/ratings/{rating}',token=token_a)
        assert removed['code']=='COMMON200' and removed['result'] is None
        assert request('삭제 후 공개 목록', 'GET',f'/members/{a}/ratings')==[]

        bad_password = fail('틀린 비밀번호', 'POST','/auth/login',login('a@umc.com','wrong'),401,'AUTH401_1')
        bad_email = fail('없는 이메일', 'POST','/auth/login',login('none@umc.com'),401,'AUTH401_1')
        assert bad_email == bad_password
        for label, body in [('빈 비밀번호',login('a@umc.com','')),('이메일 형식',login('invalid')),('누락',{})]:
            fail('로그인 검증 '+label,'POST','/auth/login',body,400,'COMMON4001')
        fail('토큰 없이 내 정보', 'GET','/members/me',None,401,'AUTH401_2')
        me = request('토큰으로 내 정보', 'GET','/members/me',token=token_a)['result']
        assert set(me)=={'email','nickname','createdAt'} and me['email']=='a@umc.com'
        assert request('B 본인 정보 분리','GET','/members/me',token=token_b)['result']['email']=='b@umc.com'
        parts = token_a.split('.')
        # Replace exactly one character in the payload, leaving the original signature intact.
        position = len(parts[1])//2
        replacement = 'A' if parts[1][position]!='A' else 'B'
        tampered = '.'.join([parts[0],parts[1][:position]+replacement+parts[1][position+1:],parts[2]])
        fail('payload 한 글자 변조', 'GET','/members/me',None,401,'AUTH401_3',tampered)
        fail('깨진 토큰', 'GET','/members/me',None,401,'AUTH401_3','not.a.jwt')
        for value in ['Basic abc', 'Bearer', '']:
            fail('Bearer 형식 누락 '+value,'GET','/members/me',None,401,'AUTH401_2',authorization=value)
        renamed = request('내 닉네임 수정', 'PATCH','/members/me',{'nickname':'영화팬칠주'},token=token_a)['result']
        assert renamed['nickname']=='영화팬칠주'
        assert request('닉네임 수정 재조회','GET','/members/me',token=token_a)['result']['nickname']=='영화팬칠주'
        request('본인 닉네임 유지 허용','PATCH','/members/me',{'nickname':'영화팬칠주'},token=token_a)
        fail('다른 회원 닉네임 중복','PATCH','/members/me',{'nickname':'영화팬B'},409,'MEMBER409_1',token_a)
        for nickname in ['', '가','가'*13,None]:
            fail('닉네임 검증 '+str(nickname),'PATCH','/members/me',{'nickname':nickname},400,'COMMON4001',token_a)
        assert query(f'SELECT nickname FROM member WHERE member_id={a};','umc_movie').splitlines()[1]=='영화팬칠주'

        # Body/query identities cannot replace the verified request attribute.
        spoof = request('Body와 query memberId 무시','POST',f'/ratings?memberId={a}',
            {'movieId':155,'score':3,'memberId':a},201,token=token_b)['result']['ratingId']
        assert query(f'SELECT member_id FROM rating WHERE rating_id={spoof};','umc_movie').splitlines()[1]==str(b)
        fail('남의 평점 삭제','DELETE',f'/ratings/{spoof}',None,403,'RATING403_1',token_a)
        assert len(request('권한 거절 후 B 평점 유지','GET',f'/members/{b}/ratings'))==1
        request('B 평점 정리','DELETE',f'/ratings/{spoof}',token=token_b)
        fail('삭제된 평점 수정','PATCH',f'/ratings/{rating}',{'score':3},404,'RATING404_1',token_a)
        fail('없는 회원 조회','GET','/members/99999/ratings',None,404,'MEMBER404_1')
        for body in [{'score':3},{'movieId':0,'score':3},{'movieId':8,'score':0},
                     {'movieId':8,'score':6},{'movieId':8,'score':4.5},{'movieId':8,'score':3,'comment':'가'*501}]:
            fail('평점 입력 검증','POST','/ratings',body,400,'COMMON4001',token_a)
        fail('검증 전에 인증','POST','/ratings',{},401,'AUTH401_2')
        fail('잘못된 JSON', 'POST','/ratings',None,400,'COMMON4001',token_a,raw_body='{')
        fail('숫자가 아닌 평점 ID','DELETE','/ratings/abc',None,400,'COMMON4001',token_a)
        # Public reads are retained, but the old writes must never work.
        request('이전 등록 경로 제거','POST',f'/members/{a}/ratings',{'movieId':8,'score':3},405)
        request('이전 수정 경로 제거','PATCH',f'/members/{a}/ratings/1',{'score':3},404,token=token_a)
        request('공개 닉네임 체크 유지','GET','/members/nickname/unused')
        request('공개 이메일 체크 유지','GET','/members/email/unused@example.com')
        preflight = urllib.request.Request(f'http://127.0.0.1:{port}/ratings',method='OPTIONS',
            headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST',
                     'Access-Control-Request-Headers':'authorization,content-type'})
        with urllib.request.urlopen(preflight,timeout=5) as response:
            assert response.status==200
            assert response.headers['Access-Control-Allow-Origin']=='http://localhost:5173'
            assert 'authorization' in response.headers['Access-Control-Allow-Headers'].lower()
        assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        metadata = {'passed':True,'http_cases':len(cases),'mysql_version':version,
            'executed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
            'scenario_9_steps':True,'login_failures_identical':True,'bcrypt_salts_differ':True,
            'jwt_required_claims':payload,'tampered_payload_rejected':True,'ownership_and_persistence':True,
            'memberId_body_query_cannot_spoof':True,'cors_preflight':True,'delete_200_null_result':True,
            'fixture_sha256':hashes}
        (RESULTS/'http-results.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (RESULTS/'verification.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        runtime = ROOT/'.validation-runtime'
        runtime.mkdir(exist_ok=True)
        (runtime/'capture-data.json').write_text(json.dumps({'a':a,'b':b,'tokenA':token_a,'tokenB':token_b,
            'tamperedToken':tampered},ensure_ascii=False),encoding='utf-8')
        print(f'PASS: {len(cases)} HTTP cases + CORS preflight, 9-step scenario and MySQL persistence.',flush=True)
        if args.serve:
            stop=ROOT/'.validation-runtime/stop'
            stop.parent.mkdir(exist_ok=True)
            stop.unlink(missing_ok=True)
            print(f'API: http://localhost:{port}; create .validation-runtime/stop to stop.',flush=True)
            while not stop.exists():
                if app.poll() is not None or db.poll() is not None:
                    raise RuntimeError('An isolated server exited unexpectedly')
                time.sleep(1)
    finally:
        if app is not None and app.poll() is None:
            app.terminate()
            app.wait(timeout=20)
        if db.poll() is None:
            try:
                query('SHUTDOWN;')
                db.wait(timeout=20)
            except Exception:
                db.terminate()
                db.wait(timeout=20)
        app_log.close()
        db_log.close()
        print('Isolated Spring/MySQL processes stopped.', flush=True)


if __name__ == '__main__':
    main()
