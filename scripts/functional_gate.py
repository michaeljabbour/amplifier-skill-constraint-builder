#!/usr/bin/env python3
"""Meaningful local functional checks; no provider calls or production activation."""
import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

S=ROOT/'skills/constraint-builder/scripts'
sys.path.insert(0,str(S))
from check_actions import evaluate
class Gate(unittest.TestCase):
    def test_boundary_rejects_escape_and_preserves_legal_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'candidate.py'
            p.write_text("from pathlib import Path\ndef validate_action(state,action):\n p=(Path(state['project_root'])/action['parameters']['path']).resolve()\n ok=p.is_relative_to(Path(state['project_root']).resolve()) and action['tool_name']=='read'\n return ok, '' if ok else 'outside boundary or unsupported action'\n")
            r=evaluate(p,[{'tool_name':'read','parameters':{'path':'note.txt'},'expected':True},{'tool_name':'read','parameters':{'path':'../outside'},'expected':False},{'tool_name':'write','parameters':{'path':'note.txt'},'expected':False}],d)
            self.assertEqual(r['illegal_escapes'],0);self.assertEqual(r['false_rejections'],0)
    def test_broken_checker_cannot_pass_as_true(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.py';p.write_text("def is_legal_action(tool,params): return 'yes'\n")
            r=evaluate(p,[{'tool_name':'read','parameters':{},'expected':False}])
            self.assertFalse(r['cases'][0]['allowed']);self.assertIn('invalid result',r['cases'][0]['reason'])

if __name__=='__main__':unittest.main(verbosity=2)
