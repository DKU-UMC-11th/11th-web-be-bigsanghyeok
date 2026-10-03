"""Run the unchanged practice SQL on an isolated, temporary local MySQL server."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import runpy
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
BIN = Path(os.environ.get('MYSQL_BIN', 'C:/Program Files/MySQL/MySQL Server 26.7/bin'))
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def process(args, **kwargs):
    return subprocess.run([str(a) for a in args], capture_output=True, creationflags=FLAGS, **kwargs)

def main():
    RESULTS.mkdir(exist_ok=True)
    originals = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['01_schema.sql','02_seed.sql']}
    data = Path(tempfile.mkdtemp(prefix='umc_week02_mysql_'))
    init = process([BIN/'mysqld.exe','--no-defaults','--initialize-insecure',f'--datadir={data}','--console'],timeout=120)
    if init.returncode:
        raise RuntimeError(init.stderr.decode('utf-8',errors='replace'))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    log = (data/'server.log').open('wb')
    server = subprocess.Popen([str(BIN/'mysqld.exe'),'--no-defaults',f'--datadir={data}',f'--port={port}',
        '--bind-address=127.0.0.1','--mysqlx=OFF','--skip-log-bin','--console'],stdout=log,stderr=log,creationflags=FLAGS)
    base=[BIN/'mysql.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}',
          '--user=root','--default-character-set=utf8mb4','--batch','--raw']
    def query(sql, db=None, verbose=False):
        args=base+(['--verbose'] if verbose else [])+([f'--database={db}'] if db else [])
        result=process(args,input=sql.encode('utf-8'),timeout=30)
        if result.returncode: raise RuntimeError(result.stderr.decode('utf-8',errors='replace'))
        return result.stdout.decode('utf-8').replace('\r\n','\n')
    try:
        for _ in range(100):
            if server.poll() is not None: raise RuntimeError((data/'server.log').read_text(errors='replace'))
            try:
                version=query('SELECT VERSION();').splitlines()[1]; break
            except RuntimeError: time.sleep(.25)
        else: raise RuntimeError('Temporary MySQL did not become ready')
        common='umc_week02_library'
        setup=f'CREATE DATABASE {common} CHARACTER SET utf8mb4; USE {common};\n'
        setup+=(ROOT/'01_schema.sql').read_text(encoding='utf-8')
        setup+='\nSELECT \'01_schema.sql completed\' AS execution; SHOW TABLES;\n'
        setup+=(ROOT/'02_seed.sql').read_text(encoding='utf-8')
        setup+='\nSELECT \'02_seed.sql completed\' AS execution;\n'
        tables=['users','category','book','rental','tag','book_tag','book_like','notification']
        counts=' UNION ALL '.join(f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in tables)+';'
        setup+=counts
        (RESULTS/'00_setup.txt').write_text(query(setup,verbose=True),encoding='utf-8')
        before=query(counts,common)
        actual={}
        expected=[
            'book_title\tdescription\tcategory_name\n달빛 도서관\t소설\t문학\n',
            'book_title\trented_at\tdue_at\n겨울의 편지\t2026-08-10 10:00:00\t2026-08-17 10:00:00\n',
            'book_title\ttag_name\tis_liked\n달빛 도서관\t소설\t1\n달빛 도서관\t추천\t1\n',
        ]
        for filename, want in zip(['03_mission1.sql','04_mission2.sql','05_mission3.sql'],expected):
            output=query((ROOT/filename).read_text(encoding='utf-8'),common)
            assert output==want,(filename,output)
            actual[filename]=output
            (RESULTS/(filename.removesuffix('.sql')+'.tsv')).write_text(output,encoding='utf-8')
        sql3=(ROOT/'05_mission3.sql').read_text(encoding='utf-8')
        cases={
            'tagless_unliked':(sql3.replace('b.book_id = 1','b.book_id = 2'), 'book_title\ttag_name\tis_liked\n겨울의 편지\tNULL\t0\n'),
            'different_user_unliked':(sql3.replace('bl.user_id = 1','bl.user_id = 2'), 'book_title\ttag_name\tis_liked\n달빛 도서관\t소설\t0\n달빛 도서관\t추천\t0\n'),
            'missing_book':(sql3.replace('b.book_id = 1','b.book_id = 999'), ''),
            'returned_book_excluded':((ROOT/'04_mission2.sql').read_text(encoding='utf-8').replace('r.user_id = 1','r.user_id = 2'),'')
        }
        edge_results={}
        for name,(sql,want) in cases.items():
            output=query(sql,common)
            assert output==want,(name,output)
            edge_results[name]={'passed':True,'result':output}
        assert before==query(counts,common)
        # Generate a separate extension fixture from the existing week01 logical schema.
        model=runpy.run_path(str(ROOT.parent/'week01/erd/render_erd.py'))
        ddl=[]
        for name,(_,fields) in model['TABLES'].items():
            pk=[f[0] for f in fields if 'PK' in f[2]]
            columns=[]
            for field,typ,key,nullable,desc in fields:
                columns.append(f'    `{field}` {typ.upper()}{"" if nullable else " NOT NULL"}'+(' AUTO_INCREMENT' if key=='PK' and len(pk)==1 else ''))
                if 'UK' in key: columns.append(f'    UNIQUE (`{field}`)')
                if 'FK' in key:
                    parent=re.match(r'(\w+)\.id',desc).group(1)
                    columns.append(f'    FOREIGN KEY (`{field}`) REFERENCES `{parent}` (`id`)')
            columns.append('    PRIMARY KEY ('+', '.join(f'`{f}`' for f in pk)+')')
            if name in model['UNIQUE']: columns.append('    '+model['UNIQUE'][name])
            ddl.append(f'CREATE TABLE `{name}` (\n'+',\n'.join(columns)+'\n);')
        ddl_text='-- 별도 확장 검증 DB 전용: week01 컬럼 및 키를 재현한 fixture. 운영용 CHECK/로직은 생략.\n'+'\n\n'.join(ddl)
        (ROOT/'validation/extension_schema.sql').write_text(ddl_text+'\n',encoding='utf-8')
        ext='umc_week02_reward'
        query(f'CREATE DATABASE {ext} CHARACTER SET utf8mb4;')
        query(ddl_text,ext)
        query((ROOT/'validation/extension_seed.sql').read_text(encoding='utf-8'),ext)
        result=query((ROOT/'06_extension.sql').read_text(encoding='utf-8'),ext)
        want='mission_title\tstore_name\tregion_name\tcompleted_at\tawarded_points\n카페 방문 미션\t안암 카페\t안암동\t2026-09-28 15:00:00\t300\n한식 식사 미션\t안암 식당\t안암동\t2026-09-27 12:00:00\t500\n'
        assert result==want,result
        actual['06_extension.sql']=result
        (RESULTS/'06_extension.tsv').write_text(result,encoding='utf-8')
        metadata={'engine':'MySQL','version':version,'executed_at':datetime.datetime.now().astimezone().isoformat(),
                  'isolation':'Temporary local server; separate library/reward databases; stopped after execution',
                  'schema_and_seed_sha256':originals,'row_counts':before,'queries':actual,'edge_cases':edge_results,
                  'common_data_unchanged':True,'extension_data':'Separately authored verification fixture, not the common seed'}
        (RESULTS/'verification.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        assert originals=={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in originals}
        print(f'MySQL {version}: schema + seed + 4 queries + 4 edge cases verified. Original files/data unchanged.',flush=True)
    finally:
        if server.poll() is None:
            admin=[BIN/'mysqladmin.exe','--no-defaults','--no-login-paths','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown']
            process(admin,timeout=30)
            try: server.wait(timeout=15)
            except subprocess.TimeoutExpired: server.terminate(); server.wait(timeout=15)
        log.close()

if __name__=='__main__': main()
