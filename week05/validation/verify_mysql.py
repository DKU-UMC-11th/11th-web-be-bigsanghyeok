"""Run the required ORM API checks against an isolated copy of the week05 MySQL schema."""
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
    parser.add_argument('--cors-disabled', action='store_true', help='Reproduce the workbook CORS failure before enabling it.')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    port = int(os.environ.get('SERVER_PORT', '18085'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))  # Never send test writes to an existing server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        db_port = sock.getsockname()[1]
    data = Path(tempfile.mkdtemp(prefix='umc_week05_mysql_'))
    subprocess.run([str(BIN / 'mysqld.exe'), '--no-defaults', '--initialize-insecure',
        f'--datadir={data}', '--console'], capture_output=True, check=True, timeout=120, creationflags=FLAGS)
    db_log = (data / 'server.log').open('wb')
    app_log = (RESULTS / 'server.log').open('wb')
    db = subprocess.Popen([str(BIN / 'mysqld.exe'), '--no-defaults', f'--datadir={data}',
        f'--port={db_port}', '--bind-address=127.0.0.1', '--mysqlx=OFF', '--skip-log-bin', '--console'],
        stdout=db_log, stderr=db_log, creationflags=FLAGS)
    app = None
    frontend = None
    base = [str(BIN / 'mysql.exe'), '--no-defaults', '--no-login-paths', '--protocol=TCP',
        '--host=127.0.0.1', f'--port={db_port}', '--user=root', '--default-character-set=utf8mb4', '--batch', '--raw']

    def query(sql, database=None):
        result = subprocess.run(base + ([f'--database={database}'] if database else []),
            input=sql.encode('utf-8'), capture_output=True, timeout=30, creationflags=FLAGS)
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
        return result.stdout.decode('utf-8').replace('\r\n', '\n')

    cases = []

    def request(name, path, status=200, origin=None, method='GET', extra_headers=None):
        headers = dict(extra_headers or {})
        if origin:
            headers['Origin'] = origin
        req = urllib.request.Request(f'http://127.0.0.1:{port}' + path, method=method, headers=headers)
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            text = response.read().decode('utf-8')
            try:
                value = json.loads(text)
            except ValueError:
                value = text
            record = {'name': name, 'method': method, 'url': req.full_url, 'request_headers': headers,
                'status': response.status, 'response_headers': dict(response.headers), 'response': value}
        cases.append(record)
        assert response.status == status, record
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
            DB_USER='root', DB_PASSWORD='', SERVER_PORT=str(port), SERVER_ADDRESS='127.0.0.1', CORS_ENABLED=str(not args.cors_disabled).lower())
        app = subprocess.Popen([JAVA, '-jar', str(ROOT / 'build/libs/movie-0.0.1-SNAPSHOT.jar')],
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

        from urllib.parse import quote
        assert request('닉네임: 중복', '/members/nickname/' + quote('수현')) == {'available': False}
        assert request('닉네임: 사용 가능', '/members/nickname/' + quote('새영화팬')) == {'available': True}
        assert request('이메일: 중복', '/members/email/noco%40umc.com') == {'available': False}
        assert request('이메일: 사용 가능', '/members/email/new%40example.com') == {'available': True}
        ratings = request('회원 1: 최신순 평점', '/members/1/ratings')
        assert [r['ratingId'] for r in ratings] == [2, 1]
        assert [r['movieId'] for r in ratings] == [155, 550]
        assert [r['score'] for r in ratings] == [4, 5]
        assert all(set(r) == {'ratingId','movieId','score','comment','createdAt','updatedAt'} for r in ratings)
        assert all(r['createdAt'] and r['updatedAt'] for r in ratings)
        assert len(request('회원 2: 다른 회원 데이터 분리', '/members/2/ratings')) == 1
        query("INSERT INTO member (email,password,nickname) VALUES ('empty@example.com','dummy-not-a-real-password','평점없는회원');", 'umc_movie')
        assert request('평점 없는 회원: 빈 목록', '/members/3/ratings') == []
        request('없는 회원: 404', '/members/999/ratings', 404)
        request('숫자가 아닌 회원 ID: 400', '/members/abc/ratings', 400)
        request('브라우저 출처 GET', '/members/1/ratings', origin='http://localhost:5173')
        allow = cases[-1]['response_headers'].get('Access-Control-Allow-Origin')
        assert allow == (None if args.cors_disabled else 'http://localhost:5173')
        if not args.cors_disabled:
            request('CORS preflight', '/members/1/ratings', origin='http://localhost:5173', method='OPTIONS',
                extra_headers={'Access-Control-Request-Method': 'GET'})
            assert cases[-1]['response_headers']['Access-Control-Allow-Origin'] == 'http://localhost:5173'
            request('허용하지 않은 출처 거부', '/members/1/ratings', 403, origin='http://untrusted.example')
        assert query('SELECT COUNT(*) FROM rating;', 'umc_movie').splitlines()[1] == '3'
        assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        (RESULTS/'http-results.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
        meta = {'passed':True,'http_cases':len(cases),'mysql_version':version,'cors_enabled':not args.cors_disabled,
            'executed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'fixture_sha256':hashes}
        (RESULTS/'verification.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        collection_items = []
        for case in cases:
            url = case['url'].replace(f'http://127.0.0.1:{port}', '{{baseUrl}}')
            req = {'method': case['method'], 'header': [{'key': k, 'value': v} for k,v in case['request_headers'].items()], 'url': url}
            collection_items.append({'name': case['name'], 'request': req,
                'response': [{'name': '실제 HTTP 결과', 'originalRequest': req, 'code': case['status'],
                    'header': [{'key': 'Content-Type', 'value': 'application/json'}],
                    'body': json.dumps(case['response'], ensure_ascii=False, indent=2)}],
                'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': [
                    f'pm.test("Expected status {case["status"]}", () => pm.response.to.have.status({case["status"]}));']}}]})
        collection = {'info': {'name': 'Week05 영화 평점 API',
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
            'variable': [{'key': 'baseUrl', 'value': f'http://localhost:{port}'}], 'item': collection_items}
        (ROOT / 'postman').mkdir(exist_ok=True)
        (ROOT / 'postman/week05.postman_collection.json').write_text(json.dumps(collection, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


        print(f'PASS: {len(cases)} HTTP cases and CORS verified.',flush=True)
        if args.serve:
            import sys
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',5173))
            frontend = subprocess.Popen([sys.executable,'-m','http.server','5173','--bind','127.0.0.1',
                '--directory',str(ROOT/'frontend')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=FLAGS)
            stop = ROOT / '.validation-runtime/stop'
            stop.parent.mkdir(exist_ok=True)
            stop.unlink(missing_ok=True)
            print(f'API: http://localhost:{port}; Web: http://localhost:5173/?api=http://localhost:{port}',flush=True)
            while not stop.exists():
                if app.poll() is not None or db.poll() is not None or frontend.poll() is not None:
                    raise RuntimeError('An isolated server exited unexpectedly')
                time.sleep(1)
    finally:
        if frontend is not None and frontend.poll() is None:
            frontend.terminate()
            frontend.wait(timeout=10)
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
