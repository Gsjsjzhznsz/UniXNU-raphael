#!/usr/bin/env python3
"""Decode only complete native RGB thumbnails; never infer physical panel output."""
import argparse,json,re,struct,zlib
from pathlib import Path
def write_png(path,width,height,pixels):
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 raw=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def decode(text,out):
 out.mkdir(parents=True,exist_ok=True);results=[]
 pattern=r"RPH FRAME BEGIN frame=(\d+) counter=(\d+) width=(\d+) height=(\d+) nonblack=(\d+) fb_nonblack=(\d+) mismatches=(\d+)\n(.*?)RPH FRAME END (\d+)"
 for m in re.finditer(pattern,text,re.S):
  frame,counter,width,height,nonblack,fb_nonblack,mismatches=map(int,m.groups()[:7])
  if int(m[9])!=frame or (width,height)!=(90,195):raise ValueError('Frame metadata mismatch')
  rows=re.findall(r"RPH FRAME ROW (\d+) (\d+) ([0-9a-f]+)",m[8])
  if len(rows)!=height:raise ValueError('Incomplete thumbnail rows')
  pixels=bytearray()
  for y,(f,row,raw) in enumerate(rows):
   if int(f)!=frame or int(row)!=y or len(raw)!=width*6:raise ValueError('Invalid thumbnail row')
   pixels.extend(bytes.fromhex(raw))
  path=out/f'frame-{frame:06d}.png';write_png(path,width,height,bytes(pixels))
  results.append(dict(frame=frame,counter=counter,nonblack=nonblack,framebuffer_nonblack=fb_nonblack,mismatches=mismatches,path=str(path)))
 (out/'frames.json').write_text(json.dumps(results,indent=2)+'\n');return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('console',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(decode(a.console.read_text(),a.out),indent=2))
