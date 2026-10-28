#!/usr/bin/env python3
"""Native Memory consumer plus an independent consumer share amplifier-data; no models."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]


class Gate(unittest.TestCase):
    def test_two_consumers_share_native_kernel_and_survive_restart(self):
        from amplifier_data import AmplifierStore,RUST_AVAILABLE
        self.assertTrue(RUST_AVAILABLE,'Durable acceptance requires the actual compiled native kernel')
        from amplifier_module_tool_memory.store import NativeMemoryStore
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/'shared.log');store=AmplifierStore(path=path,record_access=False)
            memory=NativeMemoryStore(store=store)
            ref=memory.file(wing='fictional-project',room='decisions',content='Fictional parser evidence remains unverified.',source='fixture-note')
            # A separate consumer knows only the general substrate API and retains
            # its own schema/scope. No Memory implementation moves into the kernel.
            scope=store.write_cell(b'fictional-second-consumer')
            artifact=store.write_cell(b'Fictional handoff: run the existing parser check.')
            store.scope(artifact,scope);store.relate(artifact,ref,'derived_from')
            rows=store.query_relational(scope=scope).output
            self.assertIn(artifact,{r['cell_ref'] for r in rows})
            self.assertNotIn(ref,{r['cell_ref'] for r in rows})
            found=memory.search(None,5,wing='fictional-project',lexical_query='parser')
            self.assertTrue(found);self.assertTrue(any('parser' in str(x).lower() for x in found))
            before=store.get_cell(artifact,record_access=False);store.kernel.drop_materialized(artifact)
            self.assertEqual(before,store.regenerate(artifact,record_access=False))
            memory.close()
            reopened=AmplifierStore(path=path,record_access=False)
            self.assertEqual(reopened.get_cell(ref,record_access=False).payload,b'Fictional parser evidence remains unverified.')
            self.assertEqual(reopened.get_cell(artifact,record_access=False).payload,b'Fictional handoff: run the existing parser check.')
            reopened.close()

    def test_standalone_native_cli_has_no_host_or_embedding_requirement(self):
        import amplifier_data
        self.assertTrue(amplifier_data.RUST_AVAILABLE, 'Install the public native Data distribution first')
        with tempfile.TemporaryDirectory() as d:
            env=dict(os.environ)
            env.pop('PYTHONPATH',None)
            base=[sys.executable,'-m','amplifier_module_tool_memory.evidence_cli','--store',str(Path(d)/'new.log')]
            def run(args):
                r=subprocess.run(base+args,cwd=d,env=env,capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
            r=run(['remember','--wing','fictional-project','--room','decisions','--content','Fictional parser evidence'])
            self.assertEqual(r['backend'],'amplifier-data-native')
            self.assertTrue(run(['search','--wing','fictional-project','--query','parser'])['hits'])
            view=run(['export','--wing','fictional-project'])
            self.assertEqual(view['format'],'memory-evidence-view/1');self.assertTrue(view['drawers'])

if __name__=='__main__':unittest.main(verbosity=2)
