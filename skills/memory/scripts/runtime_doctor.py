#!/usr/bin/env python3
"""Inspect optional Memory native prerequisites without opening or migrating data."""
from importlib import import_module,metadata,util
import json


def main():
    foundation=util.find_spec('amplifier_data') is not None
    native=False
    if foundation:
        native=bool(import_module('amplifier_data').RUST_AVAILABLE)
    try:version=metadata.version('amplifier-data')
    except metadata.PackageNotFoundError:version=None
    result={'format':'memory-runtime-doctor/1','portable_method_available':True,'foundation_installed':foundation,
            'foundation_version':version,'durable_native_kernel':native,'native_evidence_ready':foundation and native,
            'requires_host_for_evidence_cli':False,'requires_model_for_lexical_evidence':False,
            'opened_user_store':False,'migration_performed':False,
            'foundation_access':'Separate private amplifier-data source or an authorized distribution is required; this package does not change its visibility.',
            'scope':'Checks substrate presence/native availability. Host hooks, daemon, embeddings and live task acceptance require separate checks.'}
    print(json.dumps(result,indent=2));return 0 if result['native_evidence_ready'] else 2

if __name__=='__main__':raise SystemExit(main())
