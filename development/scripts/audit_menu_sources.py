#!/usr/bin/env python3
"""Audit unchanged primary UniXNU renderer and both positive QEMU geometries."""
import json,subprocess
from entry_probe import ROOT,sha
from source_pins import locked_revision

def main():
    src=ROOT/'sources/UniXNU'
    rev=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()
    assert rev==locked_revision('UniXNU')
    specs={'Ui.c':['UniXNUUiInit','UniXNUUiDrawFrame','EfiBltVideoFill','EfiBltBufferToVideo'],
           'Internal.h':['UniXNUUiInit','UniXNUMenuRun'],'Menu.c':['SetTimer','WaitForEvent'],
           'Font.c':['gCaFontGlyphs'],'Logo.c':['UniXNULogoRender']}
    refs=[]
    for name,markers in specs.items():
        path='package/UniXNUPkg/Library/UniXNULib/'+name
        raw=subprocess.check_output(['git','-C',str(src),'show',rev+':'+path])
        assert raw==(src/path).read_bytes(),path
        lines=raw.decode().splitlines()
        anchors={m:[i+1 for i,l in enumerate(lines) if m in l] for m in markers}
        assert all(anchors.values()),(name,anchors)
        refs.append(dict(repository='UniXNU/UniXNU',revision=rev,path=path,sha256=sha(raw),anchors=anchors))
    candidates=sorted((ROOT/'artifacts/menu-fixture-qemu').glob('*/report.json'))
    fixtures=[]
    for portrait in [False,True]:
        path=next(p for p in reversed(candidates) if json.loads(p.read_text()).get('passed') and json.loads(p.read_text()).get('unixnu_revision')==rev and bool(json.loads(p.read_text()).get('portrait_requested'))==portrait)
        o=json.loads(path.read_text());assert o['screenshot_captured']
        fixtures.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),geometry=o['geometry'],results=o['results']))
    report=dict(passed=True,primary_sources=refs,positive_fixtures=fixtures,generic_renderer_unmodified=True,
      controller='Port diagnostic bounded hardware counter loop; not UniXNURun or standard periodic timer support',physical_keys_verified=False,private_modules_linked=False)
    target=ROOT/'UniXNU-raphael/evidence/menu-source-audit.json'
    target.write_text(json.dumps(report,indent=2)+'\n');print(target)
if __name__=='__main__':main()
