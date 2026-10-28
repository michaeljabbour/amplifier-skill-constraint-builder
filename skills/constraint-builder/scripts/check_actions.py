#!/usr/bin/env python3
"""Evaluate supplied actions through the retained Pico constraint gate; never dispatch tools.

Loading constraints executes local Python. Inspect and trust the candidate module first.
"""
import argparse
import json
from pathlib import Path
from constraint_gate import ConstraintGate


def evaluate(path, cases, root=None):
    gate=ConstraintGate(str(path),root)
    results=[]
    for c in cases:
        if not isinstance(c,dict) or type(c.get('expected')) is not bool:
            raise ValueError('Each case needs tool_name, parameters and an explicit expected bool')
        allowed,reason=gate.check(c.get('tool_name'),c.get('parameters'))
        results.append({'name':c.get('name','unnamed'),'expected':c['expected'],'allowed':allowed,'reason':reason,'correct':allowed==c['expected']})
    legal=sum(c['expected'] for c in cases);illegal=len(cases)-legal
    blocked_legal=sum(r['expected'] and not r['allowed'] for r in results)
    escaped=sum(not r['expected'] and r['allowed'] for r in results)
    return {'cases':results,'legal_cases':legal,'illegal_cases':illegal,'false_rejections':blocked_legal,'illegal_escapes':escaped,
            'status':'pass-on-supplied-cases' if results and not blocked_legal and not escaped else 'fail-or-no-cases',
            'limitation':'No tool execution; supplied-case correctness does not establish unseen safety or task reward.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('constraints',type=Path);p.add_argument('cases',type=Path);p.add_argument('--project-root')
    a=p.parse_args()
    try:r=evaluate(a.constraints,json.loads(a.cases.read_text()),a.project_root);print(json.dumps(r,indent=2));return 0 if r['status']=='pass-on-supplied-cases' else 1
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')

if __name__=='__main__':raise SystemExit(main())
