"""Create importable Postman requests with examples from the real HTTP verification."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
cases = json.loads((ROOT/'results/http-results.json').read_text(encoding='utf-8'))


def item(name, case_index, path, tests, body=None):
    case = cases[case_index]
    request = {'method': case['method'], 'header': [], 'url': '{{baseUrl}}'+path}
    if body is not None:
        request['header'] = [{'key': 'Content-Type', 'value': 'application/json'}]
        request['body'] = {'mode': 'raw', 'raw': body, 'options': {'raw': {'language': 'json'}}}
    response_body = case['response']
    if not isinstance(response_body, str):
        response_body = json.dumps(response_body, ensure_ascii=False, indent=2)
    return {'name': name, 'request': request,
            'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': tests}}],
            'response': [{'name': '실제 HTTP 검증 응답 예시', 'originalRequest': request,
                          'status': {200: 'OK', 201: 'Created', 500: 'Internal Server Error'}[case['status']],
                          'code': case['status'], 'header': [{'key': 'Content-Type', 'value': case['content_type']}],
                          '_postman_previewlanguage': 'json' if 'json' in case['content_type'] else 'text',
                          'body': response_body}]}


collection = {
    'info': {'name': 'UMC 3주차 — Spring 실습과 필수 미션',
             'description': '위에서부터 순서대로 실행합니다. 예시는 Python HTTP 클라이언트로 실제 서버에서 얻은 결과입니다.\n도서 POST 응답은 워크북과 동일한 문자열입니다. 등록 후 GET 테스트가 createdBookId를 설정합니다.',
             'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
    'variable': [{'key': 'baseUrl', 'value': 'http://localhost:8080', 'type': 'string'}],
    'item': [
        item('01 실습 1 — 전체 도서 조회', 0, '/books', [
            'pm.test("200 OK", () => pm.response.to.have.status(200));',
            'pm.test("도서 JSON 배열", () => pm.expect(pm.response.json()).to.be.an("array"));']),
        item('02 실습 2 — 클린 코드 등록', 1, '/books', [
            'pm.test("200 OK", () => pm.response.to.have.status(200));',
            'pm.test("등록 완료", () => pm.expect(pm.response.text()).to.eql("도서 등록이 완료되었습니다!"));'],
            json.dumps({'categoryId': 1, 'title': '클린 코드', 'description': '애자일 소프트웨어 장인 정신'}, ensure_ascii=False, indent=2)),
        item('03 실습 2 — 등록 후 재조회', 2, '/books', [
            'pm.test("200 OK", () => pm.response.to.have.status(200));',
            'const books = pm.response.json();',
            'const created = books.filter(b => b.title === "클린 코드").sort((a,b) => b.book_id-a.book_id)[0];',
            'pm.test("신규 도서 조회", () => pm.expect(created).to.exist);',
            'if (created) pm.collectionVariables.set("createdBookId", created.book_id);']),
        item('04 필수 1 — 카테고리 1 조회', 3, '/books/category/1', [
            'pm.test("200 OK", () => pm.response.to.have.status(200));',
            'pm.test("카테고리 1만 포함", () => {',
            '  const books = pm.response.json();',
            '  pm.expect(books).to.be.an("array").that.is.not.empty;',
            '  pm.expect(books.every(b => b.category_id === 1)).to.eql(true);',
            '});']),
        item('05 필수 2 — 방금 등록한 도서 대여', 7, '/rentals', [
            'pm.test("201 Created", () => pm.response.to.have.status(201));',
            'pm.test("대여 기록 생성", () => pm.expect(pm.response.json().message).to.eql("도서 대여 기록이 생성되었습니다!"));'],
            '{\n  "userId": 1,\n  "bookId": {{createdBookId}}\n}'),
        item('06 실습 5 — titel 오타 체험 (예상 500)', 8, '/books', [
            'pm.test("워크북 오타 실습: 500", () => pm.response.to.have.status(500));'],
            json.dumps({'categoryId': 1, 'titel': '해리포터', 'description': '오타 체험'}, ensure_ascii=False, indent=2))
    ]
}
target = ROOT/'postman/week03.postman_collection.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(collection, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Created {target.name}: {len(collection["item"])} requests with actual response examples.')
