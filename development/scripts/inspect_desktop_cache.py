#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Read unchanged selected-system cache symbols and ARM64 instructions."""
import argparse,json,struct
from pathlib import Path
from symbolicate_desktop_user import OriginalCache,read

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--image',required=True);p.add_argument('--symbol');p.add_argument('--cfstring',type=lambda x:int(x,0));p.add_argument('--address',type=lambda x:int(x,0));p.add_argument('--bytes',type=lambda x:int(x,0),default=512);p.add_argument('--output',type=Path);a=p.parse_args()
 c=OriginalCache(a.cache);images=[v for v in c.images if a.image in v[2]];assert len(images)==1,images
 base,size,name=images[0];c.locate(base,0);symbols=c.loaded[base];matches=[]
 for value,string,kind in symbols:
  name=string if kind=='export' else read(c.symbols,c.strings+string,min(2048,c.ssize-string)).split(b'\0')[0].decode(errors='replace')
  if a.symbol and a.symbol.lower() in name.lower():matches.append(dict(address=hex(value),symbol=name))
 out=dict(image=images[0][2],matches=matches,original_files_modified=False)
 if a.cfstring is not None:out['static_cfstring']=dict(address=hex(a.cfstring),text=c.cfstring(a.cfstring),runtime_string_captured=False)
 address=a.address
 if address is None and len(matches)==1:address=int(matches[0]['address'],16)
 if address is not None:
  import capstone
  assert 0<a.bytes<=65536
  md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);rows=[]
  for i in md.disasm(c.virtual(address,a.bytes),address):
   row=dict(address=hex(i.address),instruction=i.mnemonic+' '+i.op_str)
   if i.mnemonic in ('bl','b') and i.op_str.startswith('#'):row['target']=c.locate(int(i.op_str[1:],0),0)
   rows.append(row)
  out['instructions']=rows
 text=json.dumps(out,indent=2)+'\n'
 if a.output:a.output.write_text(text)
 print(text)
if __name__=='__main__':main()
