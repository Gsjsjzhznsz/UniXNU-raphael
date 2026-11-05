#!/usr/bin/env python3
"""Strict inspector for this project's small, uncompressed diagnostic FV."""
import struct
import uuid
from entry_probe import sha, align

UFS_WRITE_GUID = 'bedac149-d758-4984-b0d7-506f21b51b16'
UFS_PAYLOAD_GUID = '468ae3b7-f083-4e2c-b9b3-a672be5a46d3'
UFS_EXTENT_GUID = '74840a8b-e26a-42d1-962a-df96cc83cb46'
SEC_GUID = '6d94ae07-9854-451e-844c-a646dc1f1b33'
CORE_GUID = 'd6a2cb7f-6a18-4e2f-b43b-9920a733700a'
RUNTIME_GUID = 'b601f8c4-43b7-4784-95b1-f4226cb40cee'
RETURN_GUID = '432b5fd6-7106-4102-9e42-14e0fdc91b34'
INPUT_GUID = 'd53f5707-7eb6-4ebe-b6c4-e390dc89f381'
GOP_GUID = 'cfa29b17-2eed-4164-bbd0-42b48bccf105'
APRIORI_GUID = 'fc510ee7-ffdc-11d4-bd41-0080c73c8881'
DARWIN_GUID = '1b64af87-8415-4b57-9b16-680d70913b9f'
PAYLOAD_GUID = '8a9e0a07-b2fc-47f1-a58b-10aac5650294'
PAYLOAD_PART1_GUID = '49c128b8-093b-4186-ae24-366f6c4d4d6f'
RAM_POLICY_GUID = 'd2cd8ed5-a64e-45d3-8b4e-3d02d1f1b0fb'
NATIVE_EARLY_GUID = '3d7c6c2f-3c93-41f6-8a43-e63fe3ea8078'
NATIVE_MMU_GUID = 'a43a362c-77b4-45a9-9313-a067dd84d726'
NATIVE_LOAD_GUID = 'd8588174-c45b-4308-910f-add8b51070b2'
KERNEL_WINDOW_GUID = '7f1a45cb-8376-40cd-aa87-198eb654a152'
RETURN_POLICY_GUID='26118cdd-1846-4ddc-b626-b6d6428845e2'
RETURN_STUB_GUID='075868e9-fbba-4bae-92c3-ad2103c264bd'
PHYSICAL_TIMER_GUID = '5f70ac56-3d20-45de-b865-ed51905d077a'
ARCH_DRIVERS = ['b8d9777e-d72a-451f-9bdb-bafb52a68415','953ff472-9b9e-4058-84cf-227daf89dc82','49ea041e-6752-42ca-b0b1-7344fe2546b7']
PAYLOAD_DRIVERS = ['cd3bafb6-50fb-4fe8-8e4e-ab74d2c1a600','6b38f7b4-ad98-40e9-9093-aca2b5a253c4','961578fe-b6b7-44c3-af35-6bc705cd2b1f','75ca63ad-fbae-4a06-92a0-f937c671251d']


def inspect_pe(raw, offset, xip=False):
    assert raw[:2] == b'MZ'
    pe = struct.unpack_from('<I', raw, 60)[0]
    assert pe + 24 <= len(raw) and raw[pe:pe + 4] == b'PE\0\0'
    machine, sections = struct.unpack_from('<HH', raw, pe + 4)
    opt_size = struct.unpack_from('<H', raw, pe + 20)[0]
    opt = pe + 24
    assert machine == 0xaa64 and struct.unpack_from('<H', raw, opt)[0] == 0x20b
    assert opt_size >= 160 and opt + opt_size + sections * 40 <= len(raw)
    entry = struct.unpack_from('<I', raw, opt + 16)[0]
    base = struct.unpack_from('<Q', raw, opt + 24)[0]
    section_alignment, file_alignment = struct.unpack_from('<II', raw, opt + 32)
    image_size, headers_size = struct.unpack_from('<II', raw, opt + 56)
    reloc_rva, reloc_bytes = struct.unpack_from('<II', raw, opt + 112 + 5 * 8)
    assert section_alignment == file_alignment and section_alignment >= 4096
    assert 0 < headers_size <= len(raw) and entry < image_size
    layout = []
    entry_file = None
    for i in range(sections):
        pos = opt + opt_size + i * 40
        name = raw[pos:pos + 8].split(b'\0')[0].decode()
        virtual_bytes, rva, size, at = struct.unpack_from('<4I', raw, pos + 8)
        flags = struct.unpack_from('<I', raw, pos + 36)[0]
        assert at + size <= len(raw) and rva + virtual_bytes <= image_size
        assert at % file_alignment == 0 and rva % section_alignment == 0
        assert at == rva, 'This FV requires directly executable, materialized XIP sections'
        if xip:
            assert virtual_bytes <= size, 'Unmaterialized BSS is not accepted by SEC XIP'
        if rva <= entry < rva + virtual_bytes:
            assert flags & 0x20000000
            entry_file = offset + at + entry - rva
        layout.append(dict(name=name, rva=rva, raw_offset=at, bytes=size, virtual_bytes=virtual_bytes, flags=flags))
    assert entry_file is not None and reloc_rva + reloc_bytes <= len(raw)
    at, end = reloc_rva, reloc_rva + reloc_bytes
    reloc_count = 0
    while at < end:
        page, size = struct.unpack_from('<II', raw, at)
        assert size >= 8 and size % 2 == 0 and at + size <= end
        for pos in range(at + 8, at + size, 2):
            item = struct.unpack_from('<H', raw, pos)[0]
            typ = item >> 12
            assert typ in (0, 10), 'Only ABSOLUTE padding and DIR64 fixups expected'
            if typ:
                assert page + (item & 0xfff) + 8 <= image_size
                reloc_count += 1
        at += size
    if xip:
        assert reloc_count
    return dict(machine=machine, subsystem=struct.unpack_from('<H',raw,opt+68)[0], image_base=base, image_size=image_size, entry_rva=entry,
                entry_file_offset=entry_file, alignment=section_alignment,
                relocation_count=reloc_count, sections=layout, sha256=sha(raw))


def inspect_fd(raw, base):
    assert raw[40:44] == b'_FVH' and struct.unpack_from('<Q', raw, 32)[0] == len(raw)
    assert str(uuid.UUID(bytes_le=raw[16:32])) == '8c8ce578-8a3d-4f1c-9935-896185c32dd3'
    header = struct.unpack_from('<H', raw, 48)[0]
    assert header % 2 == 0 and sum(struct.unpack('<' + 'H' * (header // 2), raw[:header])) & 65535 == 0
    ext = struct.unpack_from('<H', raw, 52)[0]
    at = align(ext + struct.unpack_from('<I', raw, ext + 16)[0] if ext else header, 8)
    files = []
    while at + 24 <= len(raw) and raw[at:at + 24] != b'\xff' * 24:
        h = bytearray(raw[at:at + 24])
        guid = str(uuid.UUID(bytes_le=bytes(h[:16])))
        size = int.from_bytes(h[20:23], 'little')
        typ, attributes, state = h[18], h[19], (~h[23]) & 255
        assert 24 <= size < 0xffffff and at + size <= len(raw)
        assert state & 4 and not state & 0x38
        data_checksum = h[17]
        h[17] = h[23] = 0
        assert sum(h) & 255 == 0
        assert ((sum(raw[at + 24:at + size]) + data_checksum) & 255 == 0) if attributes & 0x40 else data_checksum == 0xaa
        record = dict(guid=guid, type=typ, offset=at, bytes=size, sha256=sha(raw[at:at + size]), sections=[])
        pos = at + 24
        while typ != 0xf0 and pos + 4 <= at + size:
            n = int.from_bytes(raw[pos:pos + 3], 'little')
            section_type = raw[pos + 3]
            assert 4 <= n < 0xffffff and pos + n <= at + size
            section = dict(type=section_type, offset=pos, bytes=n)
            if section_type == 0x10:
                section['pe'] = inspect_pe(raw[pos + 4:pos + n], pos + 4, xip=guid == SEC_GUID)
            if section_type == 0x15:
                section['name'] = raw[pos + 4:pos + n].decode('utf-16-le').rstrip('\0')
            if guid == APRIORI_GUID and section_type == 0x19:
                assert (n-4)%16==0
                section['apriori_guids']=[str(uuid.UUID(bytes_le=raw[i:i+16])) for i in range(pos+4,pos+n,16)]
            if guid==KERNEL_WINDOW_GUID:
                from kernel_window import MAGIC, WINDOW, BLOCK
                assert section_type==0x19 and n>=68
                wp_magic,wp_version,wp_total,wp_base,wp_size,wp_virtual,wp_window,wp_guards=struct.unpack_from('<8Q',raw,pos+4)
                assert wp_magic==MAGIC and wp_version==1 and wp_total==n-4==64+16*wp_guards and 1<=wp_guards<=128
                assert wp_window in (WINDOW,2*WINDOW,704*1048576) and wp_size==wp_window+BLOCK and wp_base%BLOCK==0 and wp_virtual%4096==0
                assert wp_base+wp_size<1<<64
                for wp_i in range(wp_guards):
                    wp_a,wp_length=struct.unpack_from('<2Q',raw,pos+68+16*wp_i)
                    assert wp_length and wp_a+wp_length<1<<64 and not(wp_base<wp_a+wp_length and wp_a<wp_base+wp_size)
                section['kernel_window_policy_sha256']=sha(raw[pos+4:pos+n])
            if guid==UFS_PAYLOAD_GUID:
                from prepare_handset_payload import inspect_hashes
                assert typ==2 and section_type==0x19
                section['ufs_payload_hashes']=inspect_hashes(raw[pos+4:pos+n])
            if guid==UFS_EXTENT_GUID:
                from ufs_extent_plan import inspect_policy
                assert typ==2 and section_type==0x19 and n==8388
                section['ufs_extent_policy']=inspect_policy(raw[pos+4:pos+n])
            if guid==NATIVE_EARLY_GUID:
                from native_early import MAGIC
                assert typ==2 and section_type==0x19 and n in (228,260,292,356,452)
                w=struct.unpack_from('<'+str((n-4)//8)+'Q',raw,pos+4)
                assert w[0]==MAGIC and w[1] in [1,2,3,4,5,6,7,8,9] and w[8]==0x480 and w[9]==(8 if w[1]>=9 else 5 if w[1]>=8 else 3) and 0<w[10]<=(12 if w[1]>=9 else 3)*1048576 and w[11]==(0x100000 if w[1]>=9 else 0x80000 if w[1]>=4 else 0x40000) and w[12]==w[1]
                assert (w[13]>0 and w[14]>0 and ((w[1]==3 and w[15]<=6 and w[5]==208) or (w[1]==4 and w[15] in (7,8,9,10) and w[5]==304) or (w[1]>=5 and ((w[15]==11 and w[5]==0) or (w[15] in (12,13,14,15,16,17,18) and w[5]==80) or (w[15]==19 and w[5]==368) or (w[15]==20 and 16<=w[5]<=256 and w[5]%16==0))))) if w[1]>=3 else w[13:16]==(0,0,0)
                assert sum(w[17+i*4] for i in range(w[9]))==w[10]
                assert (w[1]==6)==(w[15]==14) and (w[1]==7)==(w[15] in (15,16)) and (w[1] in (8,9))==(w[15] in (17,18,19,20))
                assert n==(452 if w[1]>=9 else 356 if w[1]>=8 else 292 if w[1]>=7 else 260 if w[1]>=5 else 228)
                if w[1]>=5:
                    baseoff,topoff,sizeva,context=struct.unpack_from('<4Q',raw,pos+132+w[9]*32)
                    assert baseoff<4096 and topoff<4096 and baseoff%8==topoff%8==0 and sizeva>0 and context==208
                section['native_early_policy_sha256']=sha(raw[pos+4:pos+n])
            if guid==NATIVE_MMU_GUID:
                from native_mmu import MAGIC
                assert typ==2 and section_type==0x19 and n in (164,172)
                w=struct.unpack_from('<'+str((n-4)//8)+'Q',raw,pos+4)
                assert w[0]==MAGIC and (w[1],n) in ((1,164),(2,172)) and w[6]==65536 and w[17]==16 and w[19]==1
                assert not(w[3]%4096 or w[4]%2048 or w[5]%4096) and w[14]<=4096
                if w[1]==2:assert w[20]%4096==0 and 0<=w[20]<254*1048576
                section['native_mmu_policy_sha256']=sha(raw[pos+4:pos+n])
            if guid==NATIVE_LOAD_GUID:
                from native_load import MAGIC
                assert typ==2 and section_type==0x19 and n>=4+104
                words=struct.unpack_from('<13Q',raw,pos+4)
                assert words[0]==MAGIC and words[1] in (1,2,3) and 0<words[2]<=64 and n==4+104+40*words[2]+(64 if words[1]==3 else 32 if words[1]==2 else 0)
                if words[1]>=2:
                    trust=struct.unpack_from('<4Q',raw,pos+4+104+40*words[2])
                    start=(words[6]+4096+words[7]+4095)&~4095
                    if words[1]==3:
                        packed=struct.unpack_from('<4Q',raw,pos+4+104+40*words[2]+32)
                        assert packed[0]==start and 0<packed[1]<=8*1048576 and packed[2]<=0xffffffff and packed[3]+16<=words[7] and (packed[3]+16<=trust[3] or trust[3]+16<=packed[3])
                        assert packed[0]+packed[1]<=words[10]-2*1048576
                        start+=(packed[1]+4095)&~4095
                    assert trust[0]==start
                    assert 0<trust[1]<=16*1048576 and trust[0]+trust[1]<=words[10]-2*1048576
                    assert trust[2]<=0xffffffff and trust[3]+16<=words[7]
                assert words[4]>words[3] and words[3]<=words[5]<words[4] and words[10] in (256*1048576,512*1048576,704*1048576)
                section['native_load_policy_sha256']=sha(raw[pos+4:pos+n])
            if guid==UFS_WRITE_GUID:
                from ufs_write_probe import inspect_policy
                assert typ==2 and section_type==0x19 and n==8260
                section['ufs_write_policy']=inspect_policy(raw[pos+4:pos+n])
                section['ufs_write_policy_sha256']=sha(raw[pos+4:pos+n])
            if guid==RAM_POLICY_GUID:
                from ram_read_probe import policy
                assert section_type==0x19
                section['ram_read_policy']=policy(raw[pos+4:pos+n])
            if guid in [PAYLOAD_GUID,PAYLOAD_PART1_GUID]:
                assert section_type==0x19 and n in [1048576+4,10*1024*1024+4]
                section['payload_sha256']=sha(raw[pos+4:pos+n])
                if guid==PAYLOAD_GUID:assert raw[pos+4+510:pos+4+512]==b'\x55\xaa'
            record['sections'].append(section)
            pos = align(pos + n, 4)
        if typ == 0xf0:
            assert raw[at + 24:at + size] == b'\xff' * (size - 24)
        else:
            assert pos >= at + size
        files.append(record)
        at = align(at + size, 8)
    legacy={SEC_GUID,CORE_GUID,RUNTIME_GUID,GOP_GUID,RETURN_GUID,APRIORI_GUID}
    payload=legacy|{INPUT_GUID,PAYLOAD_GUID}|set(PAYLOAD_DRIVERS)
    external_payload=any(f['guid']==UFS_PAYLOAD_GUID for f in files)
    normalized_guids={x['guid'] for x in files if x['type']!=0xf0}
    if external_payload:
        assert not normalized_guids & {PAYLOAD_GUID,PAYLOAD_PART1_GUID}
        assert {UFS_EXTENT_GUID,RETURN_POLICY_GUID,RETURN_STUB_GUID,KERNEL_WINDOW_GUID}<=normalized_guids
        normalized_guids.remove(UFS_PAYLOAD_GUID);normalized_guids.add(PAYLOAD_GUID)
    assert normalized_guids - {UFS_WRITE_GUID,UFS_EXTENT_GUID,NATIVE_EARLY_GUID,NATIVE_MMU_GUID,NATIVE_LOAD_GUID,KERNEL_WINDOW_GUID,PAYLOAD_PART1_GUID,RETURN_POLICY_GUID,RETURN_STUB_GUID} in [legacy,legacy|{RAM_POLICY_GUID},legacy|{INPUT_GUID,RAM_POLICY_GUID},legacy|{INPUT_GUID},payload,payload|{DARWIN_GUID},payload|set(ARCH_DRIVERS),payload|set(ARCH_DRIVERS)|{DARWIN_GUID},legacy|{INPUT_GUID,ARCH_DRIVERS[0],PHYSICAL_TIMER_GUID},payload|{ARCH_DRIVERS[0],PHYSICAL_TIMER_GUID},payload|{ARCH_DRIVERS[0],PHYSICAL_TIMER_GUID,DARWIN_GUID}]
    guids={x['guid'] for x in files if x['type']!=0xf0}
    if UFS_WRITE_GUID in guids:
        assert {RETURN_POLICY_GUID,RETURN_STUB_GUID,KERNEL_WINDOW_GUID}<=guids
        assert not guids & {UFS_EXTENT_GUID,UFS_PAYLOAD_GUID,NATIVE_LOAD_GUID,NATIVE_MMU_GUID,NATIVE_EARLY_GUID}
    if UFS_EXTENT_GUID in guids:assert {RETURN_POLICY_GUID,RETURN_STUB_GUID,KERNEL_WINDOW_GUID}<=guids
    if NATIVE_EARLY_GUID in guids:assert NATIVE_MMU_GUID in guids
    if NATIVE_MMU_GUID in guids:assert NATIVE_LOAD_GUID in guids
    if NATIVE_LOAD_GUID in guids:
        assert {DARWIN_GUID,KERNEL_WINDOW_GUID,RETURN_POLICY_GUID,RETURN_STUB_GUID}<=guids
        assert ({UFS_PAYLOAD_GUID} if external_payload else {PAYLOAD_GUID,PAYLOAD_PART1_GUID})<=guids
    if guids & {RETURN_POLICY_GUID,RETURN_STUB_GUID}:
        assert {RETURN_POLICY_GUID,RETURN_STUB_GUID,KERNEL_WINDOW_GUID}<=guids
        for f in files:
            if f['guid'] in [RETURN_POLICY_GUID,RETURN_STUB_GUID]:
                assert f['type']==2 and len(f['sections'])==1 and f['sections'][0]['type']==0x19
                sec=f['sections'][0];data=raw[sec['offset']+4:sec['offset']+sec['bytes']]
                if f['guid']==RETURN_POLICY_GUID:
                    assert len(data)==96 and struct.unpack_from('<2Q',data)==(int.from_bytes(b'RPHRET01','little'),1)
                else: assert 0<len(data)<=0x20000
    native_chunks=[f for f in files if f['guid'] in [PAYLOAD_GUID,PAYLOAD_PART1_GUID]]
    if PAYLOAD_PART1_GUID in guids:
        assert len(native_chunks)==2 and all(f['sections'][0]['bytes']==10*1024*1024+4 for f in native_chunks)
    else:
        assert all(f['sections'][0]['bytes']==1048576+4 for f in native_chunks)
    apriori=next(x['apriori_guids'] for f in files for x in f['sections'] if 'apriori_guids' in x)
    expected=[RUNTIME_GUID]+([ARCH_DRIVERS[0],PHYSICAL_TIMER_GUID] if PHYSICAL_TIMER_GUID in guids else ARCH_DRIVERS if ARCH_DRIVERS[0] in guids else [])+[GOP_GUID]+([INPUT_GUID] if INPUT_GUID in guids else [])+(PAYLOAD_DRIVERS if PAYLOAD_GUID in guids or external_payload else [])
    assert apriori==expected
    for file in files:
        if file['type']==0xf0:continue
        expected_type=3 if file['guid']==SEC_GUID else 5 if file['guid']==CORE_GUID else 2 if file['guid'] in [UFS_WRITE_GUID,UFS_PAYLOAD_GUID,UFS_EXTENT_GUID,APRIORI_GUID,PAYLOAD_GUID,PAYLOAD_PART1_GUID,DARWIN_GUID,RAM_POLICY_GUID,NATIVE_EARLY_GUID,NATIVE_MMU_GUID,NATIVE_LOAD_GUID,KERNEL_WINDOW_GUID,RETURN_POLICY_GUID,RETURN_STUB_GUID] else 7
        assert file['type']==expected_type
        if file['guid'] in [UFS_WRITE_GUID,UFS_PAYLOAD_GUID,UFS_EXTENT_GUID,PAYLOAD_GUID,PAYLOAD_PART1_GUID,RAM_POLICY_GUID,NATIVE_EARLY_GUID,NATIVE_MMU_GUID,NATIVE_LOAD_GUID,KERNEL_WINDOW_GUID]:assert len(file['sections'])==1
        if file['guid']==DARWIN_GUID:
            assert len(file['sections'])==1 and file['sections'][0]['type']==0x10
            assert file['sections'][0]['pe']['subsystem']==11
            assert DARWIN_GUID not in apriori, 'Darwin is loaded after memory text console installation'
    assert raw[at:] == b'\xff' * (len(raw) - at)
    branch = struct.unpack_from('<I', raw)[0]
    assert branch & 0xfc000000 == 0x14000000
    sec = next(x for x in files if x['guid'] == SEC_GUID)
    pe = next(x['pe'] for x in sec['sections'] if 'pe' in x)
    assert pe['image_base'] + pe['entry_rva'] == base + pe['entry_file_offset']
    assert (branch & 0x3ffffff) * 4 == pe['entry_file_offset']
    runtime = next(x for x in files if x['guid'] == RUNTIME_GUID)
    assert next(x['pe']['alignment'] for x in runtime['sections'] if 'pe' in x) == 65536
    return dict(passed=True, fd_bytes=len(raw), sha256=sha(raw), fd_base=base,
                sec_entry=base + pe['entry_file_offset'], files=files)
