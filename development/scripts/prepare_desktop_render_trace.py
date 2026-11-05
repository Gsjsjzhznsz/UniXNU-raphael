#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Qualify read-only render-chain probes against the unchanged selected cache."""
import argparse,json
from pathlib import Path
from symbolicate_desktop_user import OriginalCache

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=OriginalCache(a.cache)
 specs=[
 ('render_for_time',0x18951dde0,'__ZN2CA12WindowServer6Server15render_for_timeEdPK11CVTimeStampyPK17CATimingReferencej',1),
 ('render_update',0x1894c5eb0,'__ZN2CA12WindowServer11AccelServer13render_updateEPNS_6Render6UpdateERj',2),
 ('software_renderer',0x1896a880c,'__ZN2CA12WindowServer6Server11sw_rendererEv',1),
 ('software_renderer_return',0x1896a89dc,'__ZN2CA12WindowServer6Server11sw_rendererEv',1),
 ('software_draw_elements',0x189616220,None,2),
 ('framebuffer_swap_end',0x1b63cfc94,'_IOMobileFramebufferSwapEnd',4)]
 sites=[]
 for name,address,symbol,limit in specs:
  found=c.locate(address,0)
  if symbol is not None:assert found.get('symbol')==symbol,(name,found)
  assert found.get('image') and found.get('symbol') and found['offset']==(0x1d0 if name=='software_renderer_return' else 0),found
  site=dict(name=name,address=address,prefix=c.virtual(address,16).hex(),original_symbol=found,max_hits=limit)
  if name=='software_renderer_return':
   assert c.virtual(address,4)==bytes.fromhex('c0035fd6')
   site['memory']=[dict(register=0,bytes=104)]
  sites.append(site)
 report=dict(process='backboardd',sites=sites,original_files_modified=False,scope='Selected cache instruction qualification only; execution and frame production still require real runtime events',handset_executed=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),sites=len(sites)),indent=2))
if __name__=='__main__':main()
