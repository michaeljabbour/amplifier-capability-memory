"""Standalone verbatim evidence operations through Memory's actual native store."""
import argparse
import json
from pathlib import Path
from .store import NativeMemoryStore


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store',type=Path,required=True,help='Explicit new/existing native log; never auto-discovers the daemon store')
    s=p.add_subparsers(dest='operation',required=True)
    for name in ('remember','search','export'):
        q=s.add_parser(name);q.add_argument('--wing',required=True);q.add_argument('--room')
        if name=='remember':q.add_argument('--content',required=True);q.add_argument('--source',default='')
        if name=='search':q.add_argument('--query',required=True);q.add_argument('--limit',type=int,default=5)
    a=p.parse_args(argv)
    if a.operation=='remember' and (not a.room or len(a.content)>8192):p.error('Remember needs --room and content at most 8192 characters')
    if a.operation=='search' and (not a.query.strip() or not 1<=a.limit<=50):p.error('Nonempty query and limit 1..50 required')
    store=None
    try:
        store=NativeMemoryStore(path=str(a.store),record_access=False)
        if a.operation=='remember':out={'ref':str(store.file(wing=a.wing,room=a.room,content=a.content,source=a.source)),'backend':'amplifier-data-native'}
        elif a.operation=='search':out={'hits':store.search(None,a.limit,wing=a.wing,room=a.room,lexical_query=a.query),'method':'native lexical/BM25; no embedder or model'}
        else:out={'format':'memory-evidence-view/1','wing':a.wing,'room':a.room,'drawers':store.list_drawers(wing=a.wing,room=a.room,limit=10000),'limit':10000,'limits':'Evidence view, not a full-fidelity native log backup; preserve the original log for regeneration.'}
        print(json.dumps(out,indent=2,default=str));return 0
    except (ValueError,OSError,RuntimeError) as e:p.exit(2,f'{type(e).__name__}: {e}\n')
    finally:
        if store is not None:store.close()

if __name__=='__main__':raise SystemExit(main())
