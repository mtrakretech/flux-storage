"""Small validated per-user preferences, independent of changing localhost ports."""
import json
import os
import threading
from pathlib import Path

DEFAULTS={'preferred_port':0,'theme':'light','open_browser':True}


class SettingsStore:
    def __init__(self,directory):
        self.path=Path(directory)/'settings.json'
        self.lock=threading.RLock()

    def read(self):
        with self.lock:
            try:
                data=json.loads(self.path.read_text(encoding='utf-8'))
                return self.validate(data,partial=False)
            except (OSError,ValueError,TypeError):
                return dict(DEFAULTS)

    @staticmethod
    def validate(data,partial=True):
        if not isinstance(data,dict):raise ValueError('Preferences must be an object.')
        unknown=set(data)-set(DEFAULTS)
        if unknown:raise ValueError('Unknown preference: '+', '.join(sorted(unknown)))
        result={} if partial else dict(DEFAULTS)
        for key,value in data.items():
            if key=='preferred_port' and (type(value) is not int or not 0<=value<=65535):
                raise ValueError('Port must be 0 (automatic) or an integer from 1 to 65535.')
            if key=='theme' and (not isinstance(value,str) or value not in {'light','dark','system'}):
                raise ValueError('Choose Light, Dark or System theme.')
            if key=='open_browser' and type(value) is not bool:
                raise ValueError('Open-browser preference must be true or false.')
            result[key]=value
        return result

    def update(self,changes):
        with self.lock:
            result={**self.read(),**self.validate(changes)}
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix(f'.{os.getpid()}.tmp')
            temporary.write_text(json.dumps(result,indent=2),encoding='utf-8')
            os.replace(temporary,self.path)
            return result
