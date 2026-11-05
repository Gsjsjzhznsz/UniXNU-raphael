#!/usr/bin/env python3
"""Create private thumbnail from nonce-bound CPU samples; publish metadata only."""
import json
import struct
from pathlib import Path
from entry_probe import ROOT,sha
from inspect_device import read_fdt,node_path
from display_probe import decode as decode_display
from pixel_probe import decode,GRID,FIELDS


def main():
    hpath=ROOT/'UniXNU-raphael/evidence/sec-display-handoff.json';h=json.loads(hpath.read_text())
    assert all(h[k] for k in ['nonce_matched','firmware_checkpoint_passed','root_verified','boot_partition_unchanged'])
    directory=ROOT/h['private_readback'];fdt=(directory/'after.dtb').read_bytes();assert sha(fdt)==h['fdt_sha256']
    chosen=next(n for n in read_fdt(fdt).walk() if node_path(n)=='/chosen')
    raw=chosen.properties['raphael,display-pixels'];display=decode_display(chosen.properties['raphael,display-snapshot'],fdt)
    result=decode(raw,fdt,display);assert result==h['pixel_probe'] and result['cpu_sample_read_verified']
    words=struct.unpack('>'+'I'*(len(raw)//4),raw);pixels=words[len(FIELDS):len(FIELDS)+GRID*GRID]
    import zlib
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    raster=b''.join(b'\0'+bytes(channel for x in range(256) for channel in [
        (pixels[(y//4)*GRID+x//4]>>16)&255,(pixels[(y//4)*GRID+x//4]>>8)&255,pixels[(y//4)*GRID+x//4]&255])
        for y in range(256))
    thumbnail=directory/'cpu-splash-thumbnail.png'
    thumbnail.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,256,8,2,0,0,0))+
                          chunk(b'IDAT',zlib.compress(raster))+chunk(b'IEND',b''))
    result.update(kind='nonce-bound CPU splash samples and interface counters; no visible-output claim',
        handoff=str(hpath.relative_to(ROOT)),handoff_sha256=sha(hpath.read_bytes()),
        private_readback=h['private_readback'],private_build=h['private_build'],
        thumbnail_sha256=sha(thumbnail.read_bytes()),original_pixels_public=False,
        limitations=['Sparse sampling does not validate every framebuffer byte or lifetime',
            'Internal counter activity does not independently prove an external TE signal, DMA fetch or visible panel output',
            'No pixel write or GOP operation occurred'],
        analysis_sources=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in [
            ROOT/'scripts/pixel_probe.py',ROOT/'scripts/display_probe.py',ROOT/'scripts/smmu_probe.py',Path(__file__)]])
    (ROOT/'UniXNU-raphael/evidence/boot-pixel-observation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['header','unique_pixel_values','nonblack_rgb_samples','counter_activity_observed']},indent=2))
    print(thumbnail)


if __name__=='__main__':main()
