"""Verify the real HTTP API against an isolated MySQL instance (no existing DB changes)."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
BIN = Path(os.environ.get('MYSQL_BIN', 'C:/Program Files/MySQL/MySQL Server 26.7/bin'))
JAVA = Path(os.environ.get('JAVA_HOME', 'C:/Program Files/Eclipse Adoptium/jdk-21.0.12.101-hotspot')) / 'bin/java.exe'
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', help='Keep the verified server running for Postman; Ctrl+C stops both processes.')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix='umc_week03_mysql_'))
    db_port = free_port()
    api_port = int(os.environ.get('SERVER_PORT', '8080'))
    # Fail before startup if another app owns this port; never send writes to that app.
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', api_port))
    init = subprocess.run([str(BIN/'mysqld.exe'), '--no-defaults', '--initialize-insecure',
                           f'--datadir={data}', '--console'], capture_output=True, creationflags=FLAGS, timeout=120)
    if init.returncode:
        raise RuntimeError(init.stderr.decode('utf-8', errors='replace'))
    db_log = (data/'server.log').open('wb')
    app_log = (RESULTS/'server.log').open('wb')
    db = subprocess.Popen([str(BIN/'mysqld.exe'), '--no-defaults', f'--datadir={data}', f'--port={db_port}',
                           '--bind-address=127.0.0.1', '--mysqlx=OFF', '--skip-log-bin', '--console'],
                          stdout=db_log, stderr=db_log, creationflags=FLAGS)
    app = None
    base = [str(BIN/'mysql.exe'), '--no-defaults', '--no-login-paths', '--protocol=TCP', '--host=127.0.0.1',
            f'--port={db_port}', '--user=root', '--default-character-set=utf8mb4', '--batch', '--raw']

    def query(sql, database=None):
        command = base + ([f'--database={database}'] if database else [])
        result = subprocess.run(command, input=sql.encode('utf-8'), capture_output=True, creationflags=FLAGS, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
        return result.stdout.decode('utf-8').replace('\r\n', '\n')

    cases = []

    def request(name, method, path, body=None, status=200):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{api_port}{path}', data=payload, method=method,
                                     headers={'Content-Type': 'application/json'} if payload else {})
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            text = response.read().decode('utf-8')
            content_type = response.headers.get('Content-Type', '')
            value = json.loads(text) if 'json' in content_type else text
            record = {'name': name, 'method': method, 'url': req.full_url, 'request_body': body,
                      'status': response.status, 'content_type': content_type, 'response': value}
        cases.append(record)
        assert response.status == status, record
        return value

    try:
        for _ in range(120):
            if db.poll() is not None:
                raise RuntimeError((data/'server.log').read_text(errors='replace'))
            try:
                version = query('SELECT VERSION();').splitlines()[1]
                break
            except RuntimeError:
                time.sleep(.25)
        else:
            raise RuntimeError('MySQL startup timed out')
        sql_files = [ROOT.parent/'week02/01_schema.sql', ROOT.parent/'week02/02_seed.sql']
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sql_files}
        query('CREATE DATABASE study CHARACTER SET utf8mb4;')
        for file in sql_files:
            query(file.read_text(encoding='utf-8'), 'study')
        (RESULTS/'00_setup.tsv').write_text(query('SHOW TABLES;', 'study'), encoding='utf-8')
        environment = dict(os.environ, DB_URL=f'jdbc:mysql://127.0.0.1:{db_port}/study?serverTimezone=Asia/Seoul&characterEncoding=UTF-8',
                           DB_USER='root', DB_PW='', SERVER_PORT=str(api_port))
        jar = ROOT/'build/libs/study-0.0.1-SNAPSHOT.jar'
        app = subprocess.Popen([str(JAVA), '-jar', str(jar)], env=environment,
                               stdout=app_log, stderr=app_log, creationflags=FLAGS)
        for _ in range(120):
            if app.poll() is not None:
                raise RuntimeError((RESULTS/'server.log').read_text(errors='replace'))
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{api_port}/books', timeout=2) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(.5)
        else:
            raise RuntimeError('Spring startup timed out')

        books = request('실습 1: 전체 도서 조회', 'GET', '/books')
        assert len(books) == 3 and [b['book_id'] for b in books] == [1, 2, 3]
        assert all('category_id' in b and 'is_available' in b for b in books)
        created = request('실습 2: 도서 등록', 'POST', '/books',
                          {'categoryId': 1, 'title': '클린 코드', 'description': '애자일 소프트웨어 장인 정신'})
        assert created == '도서 등록이 완료되었습니다!'
        books = request('실습 2: 등록 후 재조회', 'GET', '/books')
        assert len(books) == 4 and books[-1]['title'] == '클린 코드' and books[-1]['is_available']
        for category, expected in [(1, [1, 2, 4]), (2, [3]), (999, [])]:
            found = request(f'필수 1: 카테고리 {category}', 'GET', f'/books/category/{category}')
            assert [b['book_id'] for b in found] == expected
            assert all(b['category_id'] == category for b in found)
        request('필수 1: 숫자가 아닌 경로 변수', 'GET', '/books/category/abc', status=400)
        before = query('SELECT COUNT(*) AS count FROM rental;', 'study')
        rental = request('필수 2: 대여 기록 생성', 'POST', '/rentals', {'userId': 1, 'bookId': 4}, status=201)
        assert rental['message'] == '도서 대여 기록이 생성되었습니다!'
        assert int(query('SELECT COUNT(*) FROM rental;', 'study').splitlines()[1]) == int(before.splitlines()[1]) + 1
        rental_check = query('''SELECT rental_id, user_id, book_id, rented_at, due_at, returned_at,
            TIMESTAMPDIFF(SECOND, rented_at, due_at) AS duration_seconds,
            ABS(TIMESTAMPDIFF(SECOND, rented_at, NOW())) <= 10 AS current_time_matches
            FROM rental ORDER BY rental_id DESC LIMIT 1;''', 'study')
        row = rental_check.splitlines()[1].split('\t')
        assert row[1:3] == ['1', '4'] and row[5:] == ['NULL', '604800', '1'], rental_check
        (RESULTS/'rental-db.tsv').write_text(rental_check, encoding='utf-8')

        # Deliberately leave Map input unvalidated to reproduce the workbook's No DTO exercise.
        request('실습 5: titel 오타', 'POST', '/books',
                {'categoryId': 1, 'titel': '해리포터', 'description': '오타 체험'}, status=500)
        assert query('SELECT COUNT(*) FROM book;', 'study').splitlines()[1] == '4'
        request('필수 2: 존재하지 않는 외래키', 'POST', '/rentals', {'userId': 999, 'bookId': 4}, status=500)
        assert query('SELECT COUNT(*) FROM rental;', 'study').splitlines()[1] == '3'
        injection = "'); DROP TABLE book; --"
        request('파라미터 바인딩: SQL 문자열도 제목으로 저장', 'POST', '/books',
                {'categoryId': 2, 'title': injection, 'description': None})
        safe = request('파라미터 바인딩: 테이블과 저장값 재확인', 'GET', '/books/category/2')
        assert len(safe) == 2 and safe[-1]['title'] == injection
        assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sql_files}
        (RESULTS/'http-results.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        metadata = {'passed': True, 'http_cases': len(cases), 'mysql_version': version,
                    'executed_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
                    'fixture_sha256': hashes, 'rental_duration_seconds': 604800,
                    'isolation': 'Temporary local MySQL; original week02 SQL unchanged',
                    'expected_errors': ['titel -> 500 / NOT NULL', 'invalid foreign key -> 500', 'non-numeric path -> 400']}
        (RESULTS/'verification.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'PASS: {len(cases)} HTTP cases and MySQL persistence verified.', flush=True)
        if args.serve:
            stop_file = ROOT / '.validation-runtime' / 'stop'
            stop_file.parent.mkdir(exist_ok=True)
            if stop_file.exists():
                stop_file.unlink()
            print(f'Postman base URL: http://localhost:{api_port}; Ctrl+C stops the isolated servers.', flush=True)
            while not stop_file.exists():
                if app.poll() is not None or db.poll() is not None:
                    raise RuntimeError('Verification server exited unexpectedly')
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
