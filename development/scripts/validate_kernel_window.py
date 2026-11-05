#!/usr/bin/env python3
"""Independent discrete-set checks for the read-only interval audit."""
import datetime as dt
import json
import random
import tempfile
from pathlib import Path
from audit_kernel_window import Span, merge, intersection, subtract, candidate, memblock, iomem, MAX_U64
from entry_probe import ROOT, sha


def main():
    count=0
    def check(condition):
        nonlocal count
        assert condition
        count+=1
    def reject(fn):
        try:
            fn()
        except AssertionError:
            check(True)
        else:
            raise AssertionError('Invalid input accepted')
    def cells(spans):
        return {x for s in spans for x in range(s.base,s.end)}
    for base,end in [(1,1),(2,1),(-1,1),(0,MAX_U64+1)]:
        reject(lambda:Span(base,end))
    check(merge([Span(0,2),Span(2,5),Span(1,3)])==[Span(0,5)])
    check(subtract([Span(0,8)],[Span(2,6)])==[Span(0,2),Span(6,8)])
    check(subtract([Span(0,8)],[Span(0,8)])==[])
    check(candidate(Span(0x12300000,0x223fffff),0x10000000,0x200000) is None)
    check(candidate(Span(0x12400000,0x22400000),0x10000000,0x200000)==Span(0x12400000,0x22400000))
    check(candidate(Span(MAX_U64-31,MAX_U64),32,32) is None)
    check(candidate(Span(MAX_U64-63,MAX_U64),16,16,15) is not None)
    reject(lambda:candidate(Span(0,16),8,3))
    reject(lambda:candidate(Span(0,16),8,4,4))
    check(memblock('   0: 0x0000000100000000..0x0000000100000fff')==[Span(1<<32,(1<<32)+4096)])
    reject(lambda:memblock('   1: 0x0..0x1'))
    reject(lambda:memblock('   0: 0x10..0x0f'))
    reject(lambda:memblock('unavailable'))
    check(iomem('100000000-100000fff : System RAM\n  100000000-100000003 : Kernel data')==
          [(Span(1<<32,(1<<32)+4096),'System RAM',0),(Span(1<<32,(1<<32)+4),'Kernel data',2)])
    reject(lambda:iomem('not a memory range'))
    rng=random.Random(20261028)
    for _ in range(256):
        def spans():
            return [Span(a,a+rng.randrange(1,65-a)) for a in
                    [rng.randrange(64) for _ in range(rng.randrange(9))]]
        a,b=spans(),spans()
        check(cells(merge(a))==cells(a))
        check(cells(intersection(a,b))==cells(a)&cells(b))
        check(cells(subtract(a,b))==cells(a)-cells(b))
        for result in [merge(a),intersection(a,b),subtract(a,b)]:
            check(all(x.end<y.base for x,y in zip(result,result[1:])))
        start=rng.randrange(32);end=rng.randrange(start+1,65)
        size=rng.randrange(1,33);alignment=1<<rng.randrange(5);offset=rng.randrange(alignment)
        # Enumerate individual integer starts without using the audit formulas.
        valid=[x for x in range(start,end) if x%alignment==offset and x-offset>=start and x+size<=end]
        actual=candidate(Span(start,end),size,alignment,offset)
        check((actual.base if actual else None)==(valid[0] if valid else None))
    audit_path=ROOT/'UniXNU-raphael/evidence/kernel-window-audit.json';audit=json.loads(audit_path.read_text())
    check(audit['passed'] and not audit['boot_enabled'] and not audit['new_uefi_memory_registered'])
    check(audit['darwin_minimum_window_bytes']==268435456 and audit['darwin_alignment_bytes']==2097152)
    for item in audit['candidates']:
        window=item['aligned_example'];span=Span(window['base'],window['end_exclusive'])
        check(span.base%audit['darwin_alignment_bytes']==0)
        check(span.end-span.base==audit['darwin_minimum_window_bytes'])
        for guard in audit['excluded_ranges']:
            check(not (span.base<guard['end_exclusive'] and guard['base']<span.end))
    out_root=ROOT/'artifacts/kernel-window-host';out_root.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-'),dir=out_root))
    report=dict(passed=True,checks=count,randomized_discrete_models=256,
                audit=str(audit_path.relative_to(ROOT)),audit_sha256=sha(audit_path.read_bytes()),
                source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in
                               [ROOT/'scripts/audit_kernel_window.py',Path(__file__)]],
                hardware_memory_access_verified=False,allocator_enabled=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'UniXNU-raphael/evidence/kernel-window-host.json').write_text(json.dumps(report,indent=2)+'\n')
    print(count,'interval/parser/alignment checks passed, including 256 independent set models')
    print(out)


if __name__=='__main__':
    main()
