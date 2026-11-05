#!/usr/bin/env python3
"""Sourced display recipe and independent decoding; never maps/writes hardware."""
import struct
from inspect_device import read_fdt, node_path, registers, physical

OFFSETS = [0x00, 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c, 0x20,
           0x24, 0x28, 0x30, 0x34, 0x38, 0x70, 0x170, 0x174, 0x178, 0x17c]
STATUS = ['disabled', 'no-compatible-hardware', 'invalid-description', 'gcc-clock-off',
          'display-power-off', 'display-ahb-off', 'display-mdp-off', 'collected', 'unsupported-mdss-revision']


INTF_OFFSETS = [0, 4, 0x60, 0x84, 0x90, 0xac, 0x25c, 0x284, 0x288, 0x2b4]
PP_OFFSETS = [0xa0, 0xac, 0xc8]


def route_addresses(plan):
    mdp = plan['regions']['mdp']['base']
    route = plan['routing']
    result = []
    for offset in route['ctl']:
        at = mdp + offset
        result += [at + 0x14, at + 0xf4]
        for lm in range(len(route['mixer'])):
            result += [at + (0x24 if lm == 5 else lm * 4)]
            result += [at + o + lm * 4 for o in [0x40, 0x70, 0xa0]]
    for offset in route['mixer']:
        at = mdp + offset
        result += [at, at + 4]
        result += [at + blend + reg for blend in route['blend'] for reg in [0, 4]]
    result += [mdp + offset + reg for offset in route['intf'] for reg in INTF_OFFSETS]
    result += [mdp + offset + reg for offset in route['pp'] for reg in PP_OFFSETS]
    return result


def recipe(blob, version=3):
    tree = read_fdt(blob)
    nodes = list(tree.walk())
    def find(compatible):
        found = [n for n in nodes if compatible.encode() in n.properties.get('compatible', b'').split(b'\0')]
        assert all(n.properties['compatible'].endswith(b'\0') for n in found)
        assert len(found) == 1, compatible
        return found[0]
    mdp = find('qcom,sde-kms')
    gcc = find('qcom,gcc-sm8150-v2')
    cc = find('qcom,dispcc-sm8150-v2')
    handle, = mdp.cells('sde-vdd-supply')
    gdsc = next(n for n in nodes if n.cells('phandle') == [handle])
    def first(node):
        base, size = registers(node)[0]
        return dict(base=physical(node.parent, base, size), size=size,
                    source=node_path(node) + ':reg[0]')
    regions = {name: first(n) for name, n in [('mdp', mdp), ('gcc', gcc), ('dispcc', cc), ('gdsc', gdsc)]}
    plan = dict(regions=regions, malformed_unrelated_compatible=[node_path(n) for n in nodes
                if n.properties.get('compatible') and not n.properties['compatible'].endswith(b'\0')],
                pipes=mdp.cells('qcom,sde-sspp-off'),
                pipe_types=mdp.strings('qcom,sde-sspp-type'),
                pipe_source=node_path(mdp) + ':qcom,sde-sspp-off',
                offsets=OFFSETS,
                gates=[regions['gcc']['base'] + 0xb00c, regions['gdsc']['base'],
                       regions['dispcc']['base'] + 0x2080, regions['dispcc']['base'] + 0x200c])

    if version >= 3:
        route = {k: mdp.cells('qcom,sde-' + k + '-off') for k in ['ctl', 'mixer', 'intf', 'pp']}
        route.update(blend=mdp.cells('qcom,sde-mixer-blend-op-off'),
                     blend_count=mdp.cells('qcom,sde-mixer-blendstages')[0],
                     sizes={k: mdp.cells('qcom,sde-' + k + '-size')[0] for k in ['ctl','mixer','intf','pp']},
                     interface_types=mdp.strings('qcom,sde-intf-type'),
                     source=node_path(mdp))
        handle, sid, mask = mdp.cells('iommus')
        smmu = next(n for n in nodes if n.cells('phandle') == [handle])
        assert smmu.cells('#iommu-cells') == [2]
        smmu_regions = [dict(name=name, base=physical(smmu.parent, base, size), size=size)
                        for name, (base, size) in zip(smmu.strings('reg-names'), registers(smmu))]
        plan.update(routing=route, iommu_description=dict(source=node_path(smmu),
                    compatible=smmu.strings('compatible'), regions=smmu_regions,
                    stream_id=sid, stream_match_mask=mask,
                    flags=[k for k in ['qcom,skip-init','qcom,use-3-lvl-tables','qcom,disable-atos']
                           if k in smmu.properties], hardware_registers_read=False,
                    boot_mapping_proven=False))
    return plan


def decode_routes(plan, samples):
    route = plan['routing']; mdp = plan['regions']['mdp']['base']
    ctls = []
    for i, off in enumerate(route['ctl']):
        at = mdp + off
        lm = []
        for j in range(len(route['mixer'])):
            layer = [samples[at + (0x24 if j == 5 else j * 4)]]
            layer += [samples[at + o + j * 4] for o in [0x40,0x70,0xa0]]
            if any(layer):
                code = (layer[0] & 7) | ((layer[1] & 1) << 3)
                lm.append(dict(mixer=j, layer_registers=layer, border_output=bool(layer[0] & (1<<24)),
                    vig0_rect0_stage_code=code, vig0_rect1_stage_code=layer[3] & 15,
                    vig0_rect0_blend_index=code-2 if code >= 2 else None,
                    vig0_rect0_base_stage=code == 1))
        top = samples[at + 0x14]; active = samples[at + 0xf4]
        if top or active or lm:
            ctls.append(dict(index=i, top=top, command_mode_bit=bool(top & (1<<17)),
                             interface_active_mask=active, mixers=lm))
    mixers=[]
    for i, off in enumerate(route['mixer']):
        at=mdp+off; size=samples[at+4]; op=samples[at]
        blend=[]
        for j,offset in enumerate(route['blend']):
            blend_op=samples[at+offset];alpha=samples[at+offset+4]
            blend.append(dict(index=j, op=blend_op, constant_alpha=alpha,
                              foreground_alpha=(alpha>>16)&255, background_alpha=alpha&255,
                              foreground_alpha_source=blend_op&3, background_alpha_source=(blend_op>>8)&3))
        if size or op or any(b['op'] or b['constant_alpha'] for b in blend):
            mixers.append(dict(index=i, op=op, width=size&65535,height=size>>16,blend_stages=blend))
    interfaces=[]
    for i,off in enumerate(route['intf']):
        at=mdp+off;v=lambda reg:samples[at+reg];mux=v(0x25c);auto=v(0x2b4)
        interfaces.append(dict(index=i,type=route['interface_types'][i],timing_engine_enable=v(0),
            config=v(4),config2=v(0x60),dsi_command_trigger_enable=v(0x84),panel_format=v(0x90),
            frame_count=v(0xac),pingpong_mux=mux,pingpong_selection=mux&15,
            tear_check_enable=v(0x284),tear_sync_config_vsync=v(0x288),
            autorefresh_config=auto,autorefresh_enable=bool(auto&(1<<31)),autorefresh_frame_count=auto&65535))
    pps=[dict(index=i,dsc_mode=samples[mdp+off+0xa0],data_in_swap=samples[mdp+off+0xac],
              data_out_swap=samples[mdp+off+0xc8]) for i,off in enumerate(route['pp'])]
    return dict(programmed_ctls=ctls,programmed_mixers=mixers,interfaces=interfaces,pingpong=pps,
                iommu_description=plan['iommu_description'],
                interpretation='MDSS major 5 reference semantics; programmed configuration is not proof of current pixel fetch',
                activity_proven=False,refresh_executed=False)



def decode(blob, fdt_blob):
    assert len(blob) >= 24 and len(blob) % 8 == 0
    words = struct.unpack('>' + 'Q' * (len(blob) // 8), blob)
    version, status, count = words[:3]
    if version == 4:
        from smmu_probe import decode_wire4
        return decode_wire4(words, fdt_blob, decode)
    assert version in (1, 2, 3) and 0 <= status < (9 if version == 3 else 8) and count <= (640 if version == 3 else 160)
    assert len(words) == 3 + count * 2
    pairs = list(zip(words[3::2], words[4::2]))
    assert all(value <= 0xffffffff and address % 4 == 0 for address, value in pairs)
    plan = recipe(fdt_blob, version)
    expected, expected_status = [], 7
    for i, address in enumerate(plan['gates']):
        expected.append(address)
        assert len(pairs) >= len(expected), 'missing gate sample'
        observed_address, value = pairs[i]
        assert observed_address == address
        enabled = bool(value & 0x80000000) if i == 1 else value & 0x80000001 == 1
        if i == 0 and version >= 2:
            enabled = bool(value & 1) and (not value & 0x80000000 or bool(value & 2))
        if not enabled:
            expected_status = 3 + i
            break
    if expected_status == 7:
        mdp = plan['regions']['mdp']['base']
        expected.append(mdp)
        assert len(pairs) >= len(expected) and pairs[4][0] == mdp
        if version == 3 and pairs[4][1] >> 28 != 5:
            expected_status = 8
        else:
            expected.extend(mdp + p + o for p in plan['pipes'] for o in OFFSETS)
            if version == 3:
                expected.extend(route_addresses(plan))
    assert status == expected_status
    assert [a for a, _ in pairs] == expected, 'read sequence violated power/clock gates'
    samples = dict(pairs)
    programmed = []
    if status == 7:
        mdp = plan['regions']['mdp']['base']
        for i, offset in enumerate(plan['pipes']):
            at = mdp + offset
            value = lambda reg: samples[at + reg]
            src, out, fmt = value(0), value(0x0c), value(0x30)
            if not any(value(o) for o in [0, 0x0c, 0x14, 0x30]):
                continue
            programmed.append(dict(index=i, type=plan['pipe_types'][i], register_base=at,
                source_width=src & 0xffff, source_height=src >> 16,
                output_width=out & 0xffff, output_height=out >> 16,
                source_xy=value(8), output_xy=value(0x10),
                plane_address_registers=[value(o) for o in [0x14, 0x18, 0x1c, 0x20]],
                stride0=value(0x24) & 0xffff, stride1=value(0x24) >> 16,
                source_format=fmt, unpack_pattern=value(0x34), op_mode=value(0x38),
                fetch_mode=(fmt >> 30) & 3, bytes_per_pixel=((fmt >> 9) & 3) + 1,
                multirect_opmode=value(0x170), secure_address_status=value(0x70),
                active_scanout_proven=False, framebuffer_physical_mapping_proven=False))
    result = dict(version=version, status=status, status_name=STATUS[status], sample_count=count,
                samples=[dict(address=a, address_hex=hex(a), value=v, value_hex=hex(v)) for a,v in pairs],
                programmed_pipes=programmed, gates_and_read_sequence_verified=True,
                hardware_revision=samples.get(plan['regions']['mdp']['base']),
                gop_validated=False, framebuffer_writes=False,
                limitations=['Programmed pipes can be stale; active routing and command-mode refresh are not proven',
                             'Address register values are not a general physical mapping or ownership grant',
                             'No display, power, clock, SMMU or pixel-buffer register is written'])

    if version == 3 and status == 7:
        result['routing'] = decode_routes(plan, samples)
    return result
