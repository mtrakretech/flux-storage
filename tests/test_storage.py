import json
import os
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

from app import State, create_app
from engine import Policy, Cancelled, export_csv, measure_for_cleanup, scan, topmost, within


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='flux-test-',dir=os.environ.get('FLUX_TEST_TEMP'))
        self.home = Path(self.temp.name)
        self.project = self.home / 'Desktop' / 'sample'
        self.deps = self.project / 'node_modules'
        self.deps.mkdir(parents=True)
        (self.project / 'package.json').write_text('{}')
        (self.project / 'package-lock.json').write_text('{}')
        (self.deps / 'sample.js').write_text('hello')
        self.policy = Policy(self.home, self.home / 'application')
        self.state = State(self.home / 'data', self.policy)
        self.state.snapshot = scan(str(self.project), self.policy)
        self.state.index = {r['id']:r for r in self.state.snapshot['nodes']}
        self.row = next(r for r in self.state.snapshot['nodes'] if r['path']==str(self.deps))
        self.app = create_app(self.state,port=8765)
        self.client = self.app.test_client()
        self.headers = {'X-Flux-Token':self.state.token}

    def tearDown(self):
        self.temp.cleanup()

    def post(self,path,data,headers=None):
        return self.client.post(path,json=data,base_url='http://127.0.0.1:8765',headers=self.headers if headers is None else headers)

    def wait(self):
        self.assertTrue(self.state.operation.acquire(timeout=15))
        self.state.operation.release()

    def test_scan_sizes_and_manifest_policy(self):
        self.assertEqual(self.row['bytes'],5)
        self.assertTrue(self.row['eligible'])
        self.assertFalse(self.policy.describe(self.project)['eligible'])
        (self.project / 'package-lock.json').unlink()
        self.assertFalse(self.policy.describe(self.deps)['eligible'])

    def test_bundled_dependencies_are_not_eligible(self):
        self.assertFalse(self.policy.describe(self.home/'AppData'/'Local'/'tool'/'node_modules')['eligible'])
        self.assertFalse(self.policy.describe(self.deps/'tool'/'node_modules')['eligible'])
        self.assertFalse(self.policy.describe('C:/Windows/Temp/node_modules')['eligible'])

    def test_generic_build_not_disposable(self):
        build = self.project / 'build'
        build.mkdir()
        self.assertFalse(self.policy.describe(build)['eligible'])
        (self.project/'pubspec.yaml').write_text('name: demo')
        self.assertTrue(self.policy.describe(build)['eligible'])
        self.assertFalse(self.policy.describe(self.project/'dist')['eligible'])

    def test_vendor_and_environment_require_real_install_markers(self):
        vendor=self.project/'vendor';vendor.mkdir()
        (self.project/'composer.json').write_text('{}')
        (self.project/'composer.lock').write_text('{}')
        self.assertFalse(self.policy.describe(vendor)['eligible'])
        (vendor/'composer').mkdir()
        (vendor/'autoload.php').write_text('<?php')
        (vendor/'composer'/'installed.json').write_text('{}')
        self.assertTrue(self.policy.describe(vendor)['eligible'])
        env=self.project/'venv';env.mkdir()
        (self.project/'requirements.txt').write_text('flask')
        self.assertFalse(self.policy.describe(env)['eligible'])
        (env/'pyvenv.cfg').write_text('home = python')
        self.assertTrue(self.policy.describe(env)['eligible'])

    def test_manual_mode_requires_admin_and_explicit_ack(self):
        source=self.project/'source.txt';source.write_text('keep until approved')
        self.state.snapshot=scan(str(self.project),self.policy)
        self.state.index={r['id']:r for r in self.state.snapshot['nodes']}
        file=next(r for r in self.state.snapshot['large_files'] if r['path']==str(source))
        with patch('app.is_admin',return_value=False):
            with self.assertRaises(ValueError):self.state.preview([file['id']],'advanced')
        with patch('app.is_admin',return_value=True):
            p=self.state.preview([file['id']],'advanced')
            with self.assertRaises(ValueError):self.state.clean(p['ticket'],'DELETE')
            self.assertTrue(source.exists())
            p=self.state.preview([file['id']],'advanced')
            self.state.clean(p['ticket'],'DELETE',True)
            self.wait()
            self.assertEqual(self.state.job['status'],'completed')
        self.assertFalse(source.exists())
        self.assertTrue((self.project/'package.json').exists())

    def test_manual_mode_still_protects_critical_paths_and_credentials(self):
        for path in ['C:/Windows/System32','C:/Program Files/App',str(self.home/'.ssh'),str(self.project/'secret.key'),str(self.home/'AppData'/'Local'/'FluxStorage'),str(self.home/'AppData'/'Local'/'Google'/'Chrome'/'User Data')]:
            self.assertFalse(self.policy.manual(path)[0],path)
        self.assertTrue(self.policy.manual(self.project/'ordinary.txt',is_file=True)[0])

    def test_live_preview_refreshes_stale_cache_measurement(self):
        (self.deps/'sample.js').write_text('updated before preview')
        p=self.state.preview([self.row['id']])
        self.assertEqual(p['bytes'],len('updated before preview'))
        self.assertEqual(self.row['bytes'],5)

    def test_runtime_style_nonce_is_allowed_but_inline_scripts_are_not(self):
        response=self.client.get('/',base_url='http://127.0.0.1:8765')
        csp=response.headers['Content-Security-Policy']
        self.assertIn("style-src 'self' 'nonce-",csp)
        self.assertIn("script-src 'self';",csp)
        self.assertNotIn('unsafe-inline',csp)
        self.assertNotIn('unsafe-eval',csp)

    def test_system_tool_actions_are_allowlisted(self):
        with patch('app.subprocess.Popen') as launch:
            self.assertEqual(self.post('/api/system-tool',{'name':'indexing-options'}).status_code,200)
            self.assertTrue(launch.call_args.args[0][0].lower().endswith('system32\\control.exe'))
            self.assertEqual(launch.call_args.args[0][1],'srchadmin.dll')
        with patch('app.subprocess.Popen') as launch:
            self.assertEqual(self.post('/api/system-tool',{'name':'arbitrary.exe'}).status_code,400)
            launch.assert_not_called()

    def test_full_control_needs_explicit_session_unlock(self):
        self.assertEqual(self.post('/api/full-control',{'enabled':True}).status_code,400)
        with patch('app.is_admin',return_value=False):
            self.assertEqual(self.post('/api/full-control',{'enabled':True,'confirmation':'ENABLE FULL CONTROL','acknowledge':True}).status_code,400)
        with patch('app.is_admin',return_value=True):
            self.assertEqual(self.post('/api/full-control',{'enabled':True,'confirmation':'ENABLE FULL CONTROL','acknowledge':True}).status_code,200)
            self.assertTrue(self.state.full_control_enabled)
            self.assertEqual(self.post('/api/full-control',{'enabled':False}).status_code,200)
            self.assertFalse(self.state.full_control_enabled)

    def test_full_control_releases_credential_data_rules_not_os_rules(self):
        secret=self.project/'example.key';secret.write_text('isolated fixture only')
        self.state.snapshot=scan(str(self.project),self.policy)
        self.state.index={r['id']:r for r in self.state.snapshot['nodes']}
        row=next(r for r in self.state.snapshot['large_files'] if r['path']==str(secret))
        with self.assertRaises(ValueError):self.state.preview([row['id']],'advanced')
        with self.assertRaises(ValueError):self.state.preview([row['id']],'full')
        with patch('app.is_admin',return_value=True):
            self.state.full_control_enabled=True
            self.state.stale=True
            preview=self.state.preview([row['id']],'full')
            self.assertEqual(preview['manifest']['files'],1)
            self.assertTrue(secret.exists())
        self.assertFalse(self.policy.full_control('C:/Windows/System32')[0])
        self.assertFalse(self.policy.full_control(self.policy.app_dir)[0])

    def test_manifest_contains_every_exact_descendant_and_csv(self):
        nested=self.deps/'nested';nested.mkdir();(nested/'b.js').write_text('second')
        p=self.state.preview([self.row['id']])
        self.assertEqual(p['manifest']['files'],2)
        self.assertEqual(p['manifest']['folders'],2)
        result=self.client.get('/api/preview/'+p['ticket']+'/manifest',base_url='http://127.0.0.1:8765').get_json()
        self.assertEqual(result['total'],4)
        self.assertEqual({r['path'] for r in result['rows']},{str(self.deps),str(nested),str(nested/'b.js'),str(self.deps/'sample.js')})
        csv=self.client.get('/api/preview/'+p['ticket']+'/manifest?format=csv',base_url='http://127.0.0.1:8765').get_data(as_text=True)
        self.assertIn(str(nested/'b.js'),csv)
        self.assertIn('Permanently delete file',csv)
        self.assertTrue((nested/'b.js').exists())

    def test_blocked_review_cannot_execute_even_with_confirmation(self):
        root=next(r for r in self.state.snapshot['nodes'] if r['path']==str(self.project))
        p=self.state.preview([self.row['id'],root['id']],review_blocked=True)
        self.assertEqual(len(p['rows']),1)
        self.assertEqual(len(p['blocked']),1)
        with self.assertRaises(ValueError):self.state.clean(p['ticket'],'DELETE',True)
        self.assertTrue(self.deps.exists())

    def test_tree_is_lazy_scoped_and_path_resolution_uses_inventory(self):
        tree=self.client.get('/api/tree',base_url='http://127.0.0.1:8765').get_json()
        self.assertEqual(tree['root']['path'],str(self.project))
        self.assertEqual(tree['rows'][0]['path'],str(self.deps))
        good=self.client.get('/api/resolve-path',query_string={'path':str(self.deps)},base_url='http://127.0.0.1:8765')
        self.assertEqual(good.status_code,200)
        bad=self.client.get('/api/tree?parent=not-scanned',base_url='http://127.0.0.1:8765')
        self.assertEqual(bad.status_code,400)

    def test_next_batch_can_live_preview_without_forced_full_rescan(self):
        second=self.project/'.next';second.mkdir();(second/'build.js').write_text('regenerable')
        self.state.snapshot=scan(str(self.project),self.policy)
        self.state.index={r['id']:r for r in self.state.snapshot['nodes']}
        row=next(r for r in self.state.snapshot['nodes'] if r['path']==str(second))
        p=self.state.preview([self.row['id']]);self.state.clean(p['ticket'],'DELETE');self.wait()
        self.assertTrue(self.state.stale)
        next_preview=self.state.preview([row['id']])
        self.assertEqual(next_preview['manifest']['files'],1)
        self.state.clean(next_preview['ticket'],'DELETE');self.wait()
        self.assertFalse(second.exists())

    def test_readonly_fixture_dependency_can_be_removed_without_acl_changes(self):
        os.chmod(self.deps/'sample.js',0o444)
        p=self.state.preview([self.row['id']])
        self.state.clean(p['ticket'],'DELETE')
        self.wait()
        self.assertEqual(self.state.job['status'],'completed')
        self.assertFalse(self.deps.exists())

    def test_drilldown_lists_live_files_and_details(self):
        response=self.client.get('/api/items?view=tree',base_url='http://127.0.0.1:8765')
        self.assertEqual(response.status_code,200)
        data=response.get_json()
        self.assertTrue(any(r.get('is_file') for r in data['rows']))
        self.assertEqual(data['folder']['path'],str(self.project))
        row=next(r for r in data['rows'] if r['path'].endswith('package.json'))
        detail=self.client.get('/api/item/'+row['id'],base_url='http://127.0.0.1:8765').get_json()
        self.assertTrue(detail['item']['exists'])
        self.assertFalse(detail['item']['delete_allowed'])

    def test_local_custom_scan_root_and_network_rejection(self):
        self.assertEqual(self.post('/api/scan',{'root':str(self.project)}).status_code,202)
        self.wait()
        self.assertEqual(self.post('/api/scan',{'root':'\\\\server\\share'}).status_code,400)

    def test_uac_launcher_requests_runas_and_handles_denial(self):
        from privileges import ensure_admin
        with patch('privileges.is_admin',return_value=True):
            self.assertTrue(ensure_admin())
        with patch('privileges.is_admin',return_value=False),patch('privileges.ctypes.windll.shell32.ShellExecuteW',return_value=42) as execute:
            self.assertFalse(ensure_admin(str(self.project/'launch.py'),[]))
            self.assertEqual(execute.call_args.args[1],'runas')
        with patch('privileges.is_admin',return_value=False),patch('privileges.ctypes.windll.shell32.ShellExecuteW',return_value=5):
            with self.assertRaises(RuntimeError):ensure_admin(str(self.project/'launch.py'),[])

    def test_preview_expiry_and_operation_lock(self):
        p=self.state.preview([self.row['id']])
        self.state.previews[p['ticket']]['expires']=0
        with self.assertRaises(ValueError):self.state.clean(p['ticket'],'DELETE')
        self.assertTrue(self.deps.exists())
        self.state.operation.acquire()
        try:
            with self.assertRaises(ValueError):self.state.preview([self.row['id']])
        finally:self.state.operation.release()

    def test_scan_http_and_exports(self):
        root=str(self.home/'Desktop')
        self.assertEqual(self.post('/api/scan',{'root':root}).status_code,202)
        self.wait()
        self.assertEqual(self.state.job['status'],'completed')
        self.assertTrue((self.state.data/'snapshot.json.gz').exists())
        response=self.client.get('/api/export?kind=dependencies',base_url='http://127.0.0.1:8765')
        self.assertEqual(response.status_code,200)
        self.assertIn(str(self.deps),response.get_data(as_text=True))
        self.assertEqual(self.post('/api/scan',{'root':'C:/arbitrary/not-allowed'}).status_code,400)

    def test_cache_allowlist_does_not_include_profile_data(self):
        chrome = self.home/'AppData'/'Local'/'Google'/'Chrome'/'User Data'
        self.assertTrue(self.policy.describe(chrome/'Default'/'Code Cache')['eligible'])
        self.assertFalse(self.policy.describe(chrome/'Default')['eligible'])
        self.assertFalse(self.policy.describe(chrome/'Default'/'Service Worker'/'CacheStorage')['eligible'])
        self.assertFalse(self.policy.describe(self.home/'AppData'/'Local'/'Packages'/'App'/'LocalCache')['eligible'])

    def test_auth_origin_and_host(self):
        self.assertEqual(self.post('/api/preview',{'ids':[self.row['id']]},{}).status_code,403)
        self.assertEqual(self.post('/api/preview',{'ids':[self.row['id']]},{**self.headers,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/status',base_url='http://evil.example:8765').status_code,403)
        response=self.client.get('/',base_url='http://127.0.0.1:8765')
        self.assertEqual(response.status_code,200)
        self.assertIn('frame-ancestors',response.headers['Content-Security-Policy'])

    def test_no_arbitrary_paths_or_protected_folder_cleanup(self):
        self.assertEqual(self.post('/api/preview',{'ids':[str(self.project)]}).status_code,400)
        root=next(r for r in self.state.snapshot['nodes'] if r['path']==str(self.project))
        self.assertEqual(self.post('/api/preview',{'ids':[root['id']]}).status_code,400)
        self.assertEqual(self.post('/api/preview',{'ids':[]}).status_code,400)
        self.assertEqual(self.post('/api/preview',[]).status_code,400)

    def test_cleanup_requires_preview_and_exact_confirmation(self):
        self.assertEqual(self.post('/api/cleanup',{'ticket':'invented','confirmation':'DELETE'}).status_code,400)
        p=self.post('/api/preview',{'ids':[self.row['id']]}).get_json()
        self.assertEqual(self.post('/api/cleanup',{'ticket':p['ticket'],'confirmation':'delete'}).status_code,400)
        self.assertTrue(self.deps.exists())

    def test_permanent_cleanup_only_deletes_selected_temp_fixture(self):
        p=self.post('/api/preview',{'ids':[self.row['id']]}).get_json()
        result=self.post('/api/cleanup',{'ticket':p['ticket'],'confirmation':'DELETE'})
        self.assertEqual(result.status_code,202)
        self.wait()
        self.assertEqual(self.state.job['status'],'completed')
        self.assertFalse(self.deps.exists())
        self.assertTrue((self.project/'package.json').exists())
        self.assertTrue(self.state.stale)
        self.assertTrue((self.state.data/'needs-rescan').exists())
        self.assertEqual(self.post('/api/preview',{'ids':[self.row['id']]}).status_code,400)

    def test_changed_contents_abort_before_deletion(self):
        p=self.state.preview([self.row['id']])
        (self.deps/'sample.js').write_text('changed after the scan')
        self.state.clean(p['ticket'],'DELETE')
        self.wait()
        self.assertEqual(self.state.job['status'],'error')
        self.assertTrue(self.deps.exists())

    def test_future_timestamp_cannot_hide_a_changed_child(self):
        future=self.deps/'future.txt';future.write_text('future')
        os.utime(future,(4070908800,4070908800))
        p=self.state.preview([self.row['id']])
        child=self.deps/'sample.js'
        child.write_text('world')
        self.state.clean(p['ticket'],'DELETE')
        self.wait()
        self.assertEqual(self.state.job['status'],'error')
        self.assertTrue(child.exists())

    def test_removed_restore_specification_blocks_cleanup(self):
        p=self.state.preview([self.row['id']])
        (self.project/'package-lock.json').unlink()
        self.state.clean(p['ticket'],'DELETE')
        self.wait()
        self.assertEqual(self.state.job['status'],'error')
        self.assertTrue(self.deps.exists())

    def test_cancel_keeps_no_partial_snapshot(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):
            scan(str(self.project),self.policy,cancel)

    def test_overlap_and_prefix_boundaries(self):
        self.assertTrue(within(self.deps,self.project))
        self.assertFalse(within(str(self.project)+'-different',self.project))
        roots=topmost([{'path':str(self.deps),'bytes':5},{'path':str(self.deps/'child'),'bytes':3}])
        self.assertEqual(len(roots),1)

    def test_dependency_csv_contains_exact_path(self):
        text=export_csv(self.state.snapshot,True)
        self.assertIn(str(self.deps),text)
        self.assertIn('newest_modified_utc',text)

    def test_junctions_are_skipped_and_cleanup_refused(self):
        target=self.home/'external';target.mkdir();(target/'precious.txt').write_text('keep')
        junction=self.deps/'linked'
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(target)],capture_output=True)
        if result.returncode:
            self.skipTest('Junction creation is not available')
        snapshot=scan(str(self.project),self.policy)
        row=next(r for r in snapshot['nodes'] if r['path']==str(self.deps))
        self.assertEqual(row['links'],1)
        self.assertFalse(row['eligible'])
        with self.assertRaises(ValueError):measure_for_cleanup(str(self.deps))
        self.assertEqual((target/'precious.txt').read_text(),'keep')


if __name__=='__main__':
    unittest.main()
