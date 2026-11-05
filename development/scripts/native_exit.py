#!/usr/bin/env python3
"""Decode all physical timer prerequisites and restoration for exit tests."""
import struct
from validate_android_return_evidence import chosen

def decode_physical(blob, build):
    from gic_probe import decode as gic_decode
    from icc_probe import decode as icc_decode
    from gic_enable_map import decode as enable_decode
    from timer_route import decode as route_decode
    from timer_irq import decode as irq_decode, linked_window
    from physical_timer import decode as physical_decode
    c=chosen(blob);p=c.properties;d=struct.unpack('>48Q',p['raphael,sec-dxe'])
    g=gic_decode(p['raphael,gic-readonly'],blob,d[11])
    i=icc_decode(p['raphael,icc-readonly'],d[11],d[9])
    e=enable_decode(p['raphael,gic-enable-map'],g)
    route=route_decode(p['raphael,timer-route'],blob,g,e,i,expect_irq=True)
    import json
    br=json.loads((build/'report.json').read_text())
    irq=irq_decode(p['raphael,timer-irq'],route,i,br['layout'],linked_window(build))
    timer=physical_decode(p['raphael,physical-timer-arch'],6,g,route,i)
    assert timer['intid']==18 and timer['frequency']==19200000
    return dict(passed=True,gic=g,icc=i,enable_map=e,route=route,irq=irq,timer=timer)
