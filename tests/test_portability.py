"""Portable startup and storage tests. Never operate on personal inventory."""
import ctypes
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from settings import SettingsStore,DEFAULTS
from runtime import bind_server,find_running,write_record,InstanceMutex
from storage import StorageMonitor,owning_drive,path_key


class PortabilityTests(unittest.TestCase):
    def test_settings_validation_and_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            store=SettingsStore(folder)
            self.assertEqual(store.read(),DEFAULTS)
            store.update({'theme':'dark','preferred_port':45678})
            self.assertEqual(store.read()['preferred_port'],45678)
            for body in ({'theme':[]},{'theme':'red'},{'preferred_port':True},{'preferred_port':65536},{'open_browser':1},{'token':'x'},[]):
                with self.assertRaises(ValueError):store.update(body)
            store.path.write_text('broken')
            self.assertEqual(store.read(),DEFAULTS)

    def test_auto_port_and_occupied_preference_fallback(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1',0));occupied.listen()
            app=Flask(__name__)
            server=bind_server(app,occupied.getsockname()[1])
            try:
                self.assertNotEqual(server.server_port,occupied.getsockname()[1])
                self.assertGreater(server.server_port,0)
                self.assertEqual(app.config['PORT'],server.server_port)
            finally:server.server_close()

    def test_runtime_identity_and_stale_record(self):
        app=Flask(__name__)
        @app.get('/api/health')
        def health():return {'app':'Flux Storage','instance_id':'fixture','is_admin':True}
        server=bind_server(app)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                write_record(folder,server.server_port,'fixture')
                self.assertEqual(find_running(folder)['port'],server.server_port)
                write_record(folder,server.server_port,'different')
                self.assertIsNone(find_running(folder))
                (Path(folder)/'runtime.json').write_text('{')
                self.assertIsNone(find_running(folder))
        finally:server.shutdown();thread.join();server.server_close()

    @unittest.skipUnless(os.name=='nt','Windows mutex')
    def test_mutex_existing_and_release(self):
        with tempfile.TemporaryDirectory() as folder:
            first=InstanceMutex(folder);second=InstanceMutex(folder)
            try:
                self.assertFalse(first.existing);self.assertTrue(second.existing)
            finally:second.close();first.close()
            third=InstanceMutex(folder)
            try:self.assertFalse(third.existing)
            finally:third.close()

    def monitor(self,mounts,probe):
        # Avoid a background enumeration racing deterministic test steps.
        with patch.object(StorageMonitor,'_run',lambda self:None):
            return StorageMonitor(enumerator=lambda:list(mounts),prober=probe,probe_timeout=.001)

    def wait_probes(self,monitor):
        deadline=time.monotonic()+2
        while monitor.inflight and time.monotonic()<deadline:time.sleep(.005)
        self.assertFalse(monitor.inflight)

    def test_network_not_probed_and_duplicate_mounts_not_double_counted(self):
        mounts=[{'path':'C:\\','type_code':3},{'path':'C:\\mounted\\','type_code':3},{'path':'Z:\\','type_code':4}]
        calls=[]
        def probe(path):
            calls.append(path)
            return {'ready':True,'total':100,'used':60,'free':40,'volume_id':'same','status':'Ready'}
        monitor=self.monitor(mounts,probe);monitor.refresh();self.wait_probes(monitor)
        try:
            view=monitor.snapshot()
            self.assertEqual(view['aggregate']['total'],100)
            self.assertNotIn('Z:\\',calls)
            self.assertEqual(len(view['drives']),3)
            self.assertEqual(owning_drive('C:\\mounted\\file',view['drives'])['path'],'C:\\mounted\\')
        finally:monitor.close()

    def test_slow_unplug_replug_cannot_publish_stale_probe(self):
        mounts=[{'path':'E:\\','type_code':2}];release=threading.Event()
        def probe(path):
            release.wait(2)
            return {'ready':True,'total':999,'used':0,'free':999}
        monitor=self.monitor(mounts,probe);monitor.refresh()
        try:
            time.sleep(.005)
            self.assertEqual(monitor.snapshot()['drives'][0]['status'],'Device not responding')
            mounts.clear();monitor.refresh();self.assertEqual(monitor.snapshot()['drives'],[])
            mounts.append({'path':'E:\\','type_code':2});monitor.refresh()
            release.set();self.wait_probes(monitor)
            self.assertNotEqual(monitor.snapshot()['drives'][0]['total'],999)
        finally:release.set();monitor.close()

    def test_probe_error_is_visible_without_http_block(self):
        def probe(path):raise OSError('fixture unplugged')
        monitor=self.monitor([{'path':'E:\\','type_code':2}],probe)
        try:
            monitor.refresh();self.wait_probes(monitor)
            row=monitor.snapshot()['drives'][0]
            self.assertFalse(row['ready']);self.assertIn('unplugged',row['error'])
        finally:monitor.close()

    @unittest.skipUnless(os.name=='nt','Windows browser discovery')
    def test_browser_fallback_and_setup_no_silent_install(self):
        from browsers import open_local_app
        with patch('browsers.installed_browsers',return_value=[]),patch('browsers.show_browser_setup',return_value=False) as chooser:
            self.assertFalse(open_local_app('http://127.0.0.1:12345'))
            chooser.assert_called_once()
        with self.assertRaises(ValueError):open_local_app('https://example.com')
        with patch('browsers.installed_browsers',return_value=[{'path':'browser.exe'}]),patch('browsers.webbrowser.open',return_value=True),patch('browsers.show_browser_setup') as chooser:
            self.assertTrue(open_local_app('http://127.0.0.1:12345'));chooser.assert_not_called()

    def test_bootstrap_install_decline_changes_nothing(self):
        import bootstrap
        with patch('bootstrap.importlib.util.find_spec',return_value=None),patch('builtins.input',return_value='n'),patch('bootstrap.venv.EnvBuilder') as creator:
            self.assertEqual(bootstrap.main(),1);creator.assert_not_called()

    @unittest.skipUnless(os.name=='nt','Windows mounted-volume policy')
    def test_volume_mount_root_blocked(self):
        from engine import Policy
        with patch('engine.is_volume_mount',return_value=True):
            self.assertFalse(Policy().manual('E:/mounted')[0])
            self.assertFalse(Policy().full_control('E:/mounted')[0])


if __name__=='__main__':unittest.main()
