"""Run the required ORM API checks against an isolated copy of the week06 MySQL schema."""
from pathlib import Path
import argparse
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
    parser.add_argument('--serve', action='store_true', help='Keep API and frontend servers running for screenshots.')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    port = int(os.environ.get('SERVER_PORT', '18086'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))  # Never send test writes to an existing server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        db_port = sock.getsockname()[1]
    data = Path(tempfile.mkdtemp(prefix='umc_week06_mysql_'))
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

    def request(name, method, path, body=None, status=200, raw_body=None):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        if raw_body is not None:
            payload = raw_body.encode()
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path, method=method, data=payload,
            headers={'Content-Type':'application/json'} if payload is not None else {})
        try:
            response = urllib.request.urlopen(req,timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read().decode('utf-8')
            value = json.loads(raw) if raw else None
            record = {'name':name,'method':method,'url':req.full_url,'request_body':body if raw_body is None else raw_body,
                'status':response.status,'response':value,'body_bytes':len(raw.encode())}
        cases.append(record)
        if response.status != status:
            (RESULTS/'failed-attempt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        assert response.status == status, record
        if method != 'GET' and status != 204 or status >= 400:
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
            DB_USER='root', DB_PASSWORD='', SERVER_PORT=str(port), SERVER_ADDRESS='127.0.0.1', CORS_ENABLED='true')
        app = subprocess.Popen([JAVA, '-jar', str(ROOT / 'build/libs/movie-write-api-0.0.1-SNAPSHOT.jar')],
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

        import zipfile
        jar = ROOT/'build/libs/movie-write-api-0.0.1-SNAPSHOT.jar'
        crypto = ROOT/'.validation-runtime/crypto'
        crypto.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(jar) as archive:
            for name in archive.namelist():
                if name.startswith(('BOOT-INF/lib/spring-security-crypto-', 'BOOT-INF/lib/spring-jcl-')) and name.endswith('.jar'):
                    (crypto/Path(name).name).write_bytes(archive.read(name))
        def count(table):
            return int(query(f'SELECT COUNT(*) FROM {table};','umc_movie').splitlines()[1])
        def signup(email='week06@example.com',nickname='영화팬06',password='Movie123!'):
            return {'email':email,'password':password,'nickname':nickname}
        assert len(request('5주차 조회 API 유지','GET','/members/1/ratings')) == 2
        created=request('실습 1 회원가입 201','POST','/members',signup(),201)
        member=created['result']['memberId']
        assert set(created['result']) == {'memberId','email','nickname'}
        stored=query(f'SELECT password FROM member WHERE member_id={member};','umc_movie').splitlines()[1]
        check=subprocess.run([JAVA,'--class-path',str(crypto/'*'),str(ROOT/'validation/VerifyPasswordHash.java'),stored],
            capture_output=True,timeout=30,creationflags=FLAGS)
        assert check.returncode == 0, check.stderr.decode(errors='replace')
        second=request('동일 테스트 비밀번호도 다른 salt 해시','POST','/members',signup('salt06@example.com','영화팬두명'),201)
        other=query(f"SELECT password FROM member WHERE member_id={second['result']['memberId']};",'umc_movie').splitlines()[1]
        assert len(stored)==60 and len(other)==60 and stored!=other
        request('중복 이메일 409','POST','/members',signup(nickname='다른닉네임'),409)
        request('중복 닉네임 409','POST','/members',signup('other06@example.com'),409)
        for label, body in [
            ('이메일 형식',signup('invalid')),
            ('이메일 빈 값',signup('')),
            ('닉네임 1자',signup(nickname='가')),
            ('닉네임 13자',signup(nickname='가'*13)),
            ('비밀번호 대문자 누락',signup(password='movie123!')),
            ('비밀번호 소문자 누락',signup(password='MOVIE123!')),
            ('비밀번호 숫자 누락',signup(password='Movieabc!')),
            ('비밀번호 특수문자 누락',signup(password='Movie1234')),
            ('비밀번호 7자',signup(password='Mov123!')),
            ('bcrypt 72바이트 초과',signup(password='Movie123!'+'가'*24)),
        ]:
            request('400 '+label,'POST','/members',body,400)
        assert count('member')==4
        rating=request('실습 3 평점 등록 201','POST',f'/members/{member}/ratings',
            {'movieId':27205,'score':4,'comment':'등록 실습'},201)['result']
        assert count('rating')==4
        request('중복 평점 409','POST',f'/members/{member}/ratings',{'movieId':27205,'score':3},409)
        assert count('rating')==4
        for label, body in [
            ('movieId 0',{'movieId':0,'score':3}),
            ('movieId 누락',{'score':3}),
            ('별점 0',{'movieId':999,'score':0}),
            ('별점 6',{'movieId':999,'score':6}),
            ('별점 누락',{'movieId':999}),
            ('소수 별점 4.5',{'movieId':999,'score':4.5}),
            ('소수 영화 ID',{'movieId':999.5,'score':4}),
            ('후기 501자',{'movieId':999,'score':3,'comment':'가'*501}),
        ]:
            request('400 '+label,'POST',f'/members/{member}/ratings',body,400)
        request('없는 회원 평점 등록 404','POST','/members/999/ratings',{'movieId':999,'score':3},404)
        before=request('수정 전 조회','GET',f'/members/{member}/ratings')[0]
        for method, body in [('PATCH',{'score':1,'comment':'다른 회원 요청'}),('DELETE',None)]:
            request('타인 평점 '+method+' 403',method,f'/members/1/ratings/{rating}',body,403)
        assert request('타인 요청 후 원본 보존','GET',f'/members/{member}/ratings')[0]==before
        request('평점 수정 200','PATCH',f'/members/{member}/ratings/{rating}',{'score':5,'comment':'수정 실습'},200)
        after=request('수정 후 실제 조회','GET',f'/members/{member}/ratings')[0]
        assert after['score']==5 and after['comment']=='수정 실습' and after['createdAt']==before['createdAt']
        assert after['updatedAt']>=before['updatedAt']
        assert query(f'SELECT score, comment FROM rating WHERE rating_id={rating};','umc_movie').splitlines()[1]=='5\t수정 실습'
        request('수정 별점 범위 오류 400','PATCH',f'/members/{member}/ratings/{rating}',{'score':0},400)
        request('평점 삭제 204 빈 Body','DELETE',f'/members/{member}/ratings/{rating}',status=204)
        assert request('삭제 후 목록 비어 있음','GET',f'/members/{member}/ratings')==[]
        assert count('rating')==3
        for method,body in [('PATCH',{'score':3}),('DELETE',None)]:
            request('없는 평점 '+method+' 404',method,f'/members/{member}/ratings/{rating}',body,404)
        boundary=request('별점 1점 후기 500자 경계','POST',f'/members/{member}/ratings',
            {'movieId':999,'score':1,'comment':'가'*500},201)['result']
        request('경계 데이터 정리','DELETE',f'/members/{member}/ratings/{boundary}',status=204)
        request('숫자가 아닌 경로 ID 400','POST','/members/abc/ratings',{'movieId':999,'score':3},400)
        request('잘못된 JSON도 공통 형식','POST','/members',status=400,raw_body='{')
        assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        metadata={'passed':True,'http_cases':len(cases),'mysql_version':version,
            'executed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
            'password_bcrypt_matches':True,'stored_hash_length':len(stored),'salt_hashes_differ':True,
            'password_not_in_signup_response':True,'duplicate_rating_not_inserted':True,
            'ownership_forbidden_and_unchanged':True,'delete_204_empty_body':True,'fixture_sha256':hashes}
        (RESULTS/'http-results.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (RESULTS/'verification.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        items=[]
        for case in cases:
            req={'method':case['method'],'header':[],'url':case['url'].replace(f'http://127.0.0.1:{port}','{{baseUrl}}')}
            if case['request_body'] is not None:
                req['header']=[{'key':'Content-Type','value':'application/json'}]
                req['body']={'mode':'raw','raw':json.dumps(case['request_body'],ensure_ascii=False,indent=2),
                    'options':{'raw':{'language':'json'}}}
            items.append({'name':case['name'],'request':req,
                'response':[{'name':'실제 실행 결과','originalRequest':req,'code':case['status'],'header':[],
                    'body':json.dumps(case['response'],ensure_ascii=False,indent=2) if case['body_bytes'] else ''}],
                'event':[{'listen':'test','script':{'type':'text/javascript','exec':[
                    f'pm.test("Expected status", () => pm.response.to.have.status({case["status"]}));']}}]})
        collection={'info':{'name':'Week06 회원가입·평점 CRUD 실습과 필수 미션',
            'schema':'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
            'variable':[{'key':'baseUrl','value':f'http://localhost:{port}'}],'item':items}
        (ROOT/'postman').mkdir(exist_ok=True)
        (ROOT/'postman/week06.postman_collection.json').write_text(json.dumps(collection,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'PASS: {len(cases)} HTTP cases, actual stored bcrypt hash and MySQL persistence verified.',flush=True)
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
