"""Run the required ORM API checks against an isolated copy of the week02 MySQL schema."""
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
    parser.add_argument('--serve', action='store_true', help='Keep the isolated servers running for Postman.')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    port = int(os.environ.get('SERVER_PORT', '18084'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))  # Never send test writes to an existing server.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        db_port = sock.getsockname()[1]
    data = Path(tempfile.mkdtemp(prefix='umc_week04_mysql_'))
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

    def request(name, method, body=None, status=200):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{port}/books', data=payload, method=method,
            headers={'Content-Type': 'application/json'} if payload else {})
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            value = json.loads(response.read().decode('utf-8'))
            record = {'name': name, 'method': method, 'url': req.full_url, 'request_body': body,
                'status': response.status, 'response': value}
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
        fixtures = [ROOT.parent / 'week02/01_schema.sql', ROOT.parent / 'week02/02_seed.sql']
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        query('CREATE DATABASE study CHARACTER SET utf8mb4;')
        for fixture in fixtures:
            query(fixture.read_text(encoding='utf-8'), 'study')
        env = dict(os.environ, DB_URL=f'jdbc:mysql://127.0.0.1:{db_port}/study?serverTimezone=Asia/Seoul&characterEncoding=UTF-8',
            DB_USER='root', DB_PW='', SERVER_PORT=str(port), SERVER_ADDRESS='127.0.0.1')
        app = subprocess.Popen([JAVA, '-jar', str(ROOT / 'build/libs/study-orm-0.0.1-SNAPSHOT.jar')],
            env=env, stdout=app_log, stderr=app_log, creationflags=FLAGS)
        for _ in range(160):
            if app.poll() is not None:
                raise RuntimeError((RESULTS / 'server.log').read_text(errors='replace'))
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/books', timeout=2):
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(.5)
        else:
            raise RuntimeError('Spring startup timed out')

        keys = {'bookId', 'title', 'description', 'categoryName', 'isAvailable'}
        books = request('GET: 최신순 및 응답 DTO', 'GET')
        assert [b['bookId'] for b in books] == [3, 2, 1]
        assert all(set(b) == keys for b in books)
        assert books[0]['categoryName'] == '과학' and books[1]['categoryName'] == '문학'
        assert books[1]['isAvailable'] is False  # Include unavailable books too.
        created = request('POST: 정상 도서 등록', 'POST',
            {'categoryId': 1, 'title': '클린 코드', 'description': 'ORM 필수 미션 등록 검증'}, 201)
        assert set(created) == keys and created['bookId'] == 4
        assert created['title'] == '클린 코드' and created['categoryName'] == '문학' and created['isAvailable'] is True
        assert request('GET: 등록 후 최신 도서 확인', 'GET')[0] == created
        optional = request('POST: 설명 생략 및 제목 100자 경계', 'POST', {'categoryId': 2, 'title': '가' * 100}, 201)
        assert optional['description'] is None and optional['categoryName'] == '과학'
        for name, body, field in [
            ('빈 제목', {'categoryId': 1, 'title': ''}, 'title'),
            ('공백 제목', {'categoryId': 1, 'title': '   '}, 'title'),
            ('제목 누락', {'categoryId': 1}, 'title'),
            ('title 대신 titel 오타', {'categoryId': 1, 'titel': '오타'}, 'title'),
            ('제목 101자', {'categoryId': 1, 'title': '가' * 101}, 'title'),
            ('카테고리 누락', {'title': '제목'}, 'categoryId'),
            ('카테고리 null', {'categoryId': None, 'title': '제목'}, 'categoryId'),
        ]:
            result = request('400: ' + name, 'POST', body, 400)
            assert result['status'] == 400 and field in result['errors'], result
        request('400: 숫자가 아닌 카테고리', 'POST', {'categoryId': 'abc', 'title': '제목'}, 400)
        missing = request('404: 존재하지 않는 카테고리', 'POST', {'categoryId': 999, 'title': '제목'}, 404)
        assert missing['detail'] == '존재하지 않는 카테고리입니다.'
        assert query('SELECT COUNT(*) FROM book;', 'study').splitlines()[1] == '5'
        assert query('SELECT category_id, title, is_available FROM book WHERE book_id=4;', 'study').splitlines()[1] == '1\t클린 코드\t1'
        # Keep clean, short sample data for the separate Postman evidence requests.
        query('DELETE FROM book WHERE book_id=5;', 'study')
        assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures}
        (RESULTS / 'http-results.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        meta = {'passed': True, 'http_cases': len(cases), 'mysql_version': version,
            'executed_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
            'fixture_sha256': hashes, 'schema_mode': 'validate', 'isolation': 'Temporary local MySQL; original week02 files unchanged'}
        (RESULTS / 'verification.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        collection_items = []
        for case in cases:
            req = {'method': case['method'], 'header': [], 'url': '{{baseUrl}}/books'}
            if case['request_body'] is not None:
                req['header'] = [{'key': 'Content-Type', 'value': 'application/json'}]
                req['body'] = {'mode': 'raw', 'raw': json.dumps(case['request_body'], ensure_ascii=False, indent=2),
                    'options': {'raw': {'language': 'json'}}}
            collection_items.append({'name': case['name'], 'request': req,
                'response': [{'name': '실제 HTTP 검증 결과', 'originalRequest': req, 'code': case['status'],
                    'header': [{'key': 'Content-Type', 'value': 'application/json'}],
                    'body': json.dumps(case['response'], ensure_ascii=False, indent=2)}],
                'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': [
                    f'pm.test("Expected status {case["status"]}", () => pm.response.to.have.status({case["status"]}));']}}]})
        collection = {'info': {'name': 'Week04 필수 미션 — ORM 도서 API',
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
            'variable': [{'key': 'baseUrl', 'value': f'http://localhost:{port}'}], 'item': collection_items}
        (ROOT / 'postman').mkdir(exist_ok=True)
        (ROOT / 'postman/week04.postman_collection.json').write_text(json.dumps(collection, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'PASS: {len(cases)} HTTP cases, DTO contract and MySQL persistence verified.', flush=True)
        if args.serve:
            stop = ROOT / '.validation-runtime/stop'
            stop.parent.mkdir(exist_ok=True)
            stop.unlink(missing_ok=True)
            print(f'Postman base URL: http://localhost:{port}; create .validation-runtime/stop to stop.', flush=True)
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
