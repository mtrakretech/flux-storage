"""Self-contained browser checks. Deletion is restricted to fresh temp fixtures.

Run after building frontend: python tests/e2e.py
Requires: python -m playwright install chromium
"""
import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright,expect
from app import State,create_app
from engine import Policy,scan
from runtime import bind_server


class FixtureStorage:
    def __init__(self,root):self.root=str(root)
    def snapshot(self):
        return {'drives':[{'id':'demo','path':self.root,'label':'Demo storage','type':'Fixed drive','type_code':3,'filesystem':'NTFS','status':'Ready','ready':True,'can_scan':True,'total':100000000000,'used':40000000000,'free':60000000000}],
                'aggregate':{'total':100000000000,'used':40000000000,'free':60000000000},'updated':0,'error':''}


def main():
    with tempfile.TemporaryDirectory(prefix='flux-e2e-',dir=os.environ.get('FLUX_TEST_TEMP')) as folder,patch('app.is_admin',return_value=True):
        home=Path(folder);project=home/'Desktop'/'demo-project'
        deps=project/'node_modules';deps.mkdir(parents=True)
        (project/'package.json').write_text('{}');(project/'package-lock.json').write_text('{}')
        (deps/'fixture.js').write_text('regenerable fixture')
        (project/'keep-source.txt').write_text('must survive')
        (project/'signing-demo.key').write_text('not a real key')
        (project/'assets'/'images').mkdir(parents=True)
        (project/'assets'/'images'/'demo.txt').write_text('synthetic')
        policy=Policy(home,home/'application');state=State(home/'state',policy,storage=FixtureStorage(project))
        state.snapshot=scan(str(project),policy);state.index={r['id']:r for r in state.snapshot['nodes']}
        app=create_app(state,port=0);server=bind_server(app)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        errors=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel=os.environ.get('FLUX_TEST_BROWSER_CHANNEL') or None)
                page=browser.new_page(viewport={'width':1440,'height':1000})
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                expect(page.get_by_role('heading',name='Your storage, in focus.')).to_be_visible()
                expect(page.get_by_role('region',name='Connected storage')).to_contain_text('Demo storage')
                expect(page.get_by_text(f'Port {server.server_port}',exact=False)).to_be_visible()
                page.get_by_role('button',name='Change color theme').click()
                page.get_by_role('menuitem',name='dark',exact=True).click()
                expect(page.locator('html')).to_have_class('dark')
                assert state.settings.read()['theme']=='dark'
                page.locator('[data-view="tree"]').click()
                expect(page.get_by_role('tree',name='Folder navigation tree')).to_be_visible()
                page.get_by_role('button',name='Expand assets',exact=True).click()
                expect(page.get_by_role('treeitem',name='images',exact=True)).to_be_visible()
                page.get_by_role('button',name='Icon view',exact=True).click()
                expect(page.get_by_test_id('explorer-tile').first).to_be_visible()
                page.get_by_role('button',name='Browse assets',exact=True).click()
                expect(page.get_by_role('button',name='Back',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Parent folder',exact=True).click()
                page.get_by_role('button',name='List view',exact=True).click()
                page.get_by_role('checkbox',name='Select signing-demo.key',exact=True).check()
                page.get_by_test_id('review-cleanup').click()
                expect(page.get_by_role('dialog')).to_contain_text('selections are blocked')
                expect(page.get_by_test_id('confirm-delete')).to_be_disabled()
                page.keyboard.press('Escape')
                page.get_by_test_id('full-control-mode').click()
                page.get_by_role('dialog').get_by_role('checkbox').check()
                page.locator('#full-control-confirmation').fill('ENABLE FULL CONTROL')
                page.get_by_test_id('unlock-full-control').click()
                expect(page.get_by_test_id('full-control-mode')).to_have_attribute('aria-pressed','true')
                expect(page.get_by_role('checkbox',name='Select signing-demo.key',exact=True)).to_be_checked()
                page.get_by_test_id('review-cleanup').click()
                expect(page.get_by_role('dialog')).to_contain_text('Permanently delete file')
                expect(page.get_by_role('dialog')).to_contain_text(str(project/'signing-demo.key'))
                page.get_by_role('dialog').get_by_role('checkbox').check()
                page.locator('#delete-confirmation').fill('DELETE')
                page.get_by_test_id('confirm-delete').click()
                expect(page.get_by_text('Cleanup changed your files.',exact=False)).to_be_visible(timeout=15000)
                assert not (project/'signing-demo.key').exists()
                assert (project/'keep-source.txt').exists()
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                assert not errors,errors
                browser.close()
            print('Fixture-only E2E passed: storage, dynamic port, theme, tree/grid/navigation, blocked preview, risky unlock, exact manifest, deletion and source preservation, mobile width.')
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()


if __name__=='__main__':main()
