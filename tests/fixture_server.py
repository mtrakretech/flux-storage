"""Isolated browser-test server. All deletable content is newly created test data."""
import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import State,create_app
from engine import Policy,scan
from runtime import bind_server

with tempfile.TemporaryDirectory(prefix='flux-browser-fixture-',dir=os.environ.get('FLUX_TEST_TEMP')) as temporary:
    home=Path(temporary)
    project=home/'Desktop'/'sample-project'
    deps=project/'node_modules';deps.mkdir(parents=True)
    (project/'package.json').write_text('{}')
    (project/'package-lock.json').write_text('{}')
    (deps/'sample.js').write_text('isolated test dependency')
    (project/'notes.txt').write_text('test file for manual removal')
    (project/'keep-source.txt').write_text('must survive both cleanup flows')
    (project/'signing-demo.key').write_text('isolated test key, not a real credential')
    (project/'assets'/'images').mkdir(parents=True)
    (project/'assets'/'images'/'logo.txt').write_text('isolated nested test asset')
    policy=Policy(home,home/'application')
    state=State(home/'state',policy)
    state.snapshot=scan(str(project),policy)
    state.index={r['id']:r for r in state.snapshot['nodes']}
    app=create_app(state,port=0)
    server=bind_server(app)
    print(f'Fixture server ready: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
