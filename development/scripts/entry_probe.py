#!/usr/bin/env python3
"""Build a position-independent Linux-entry probe, never a complete UEFI FD.

The private Android image is patched only at its first B and image_size. A
completed probe restores both before continuing to the original B target at
the same PA. Unsupported entry CPU state bypasses instrumentation directly.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'UniXNU-raphael/package/firmware/RaphaelPkg/EntryProbe'
LIBFDT = ROOT / 'sources/mu_basecore/MdePkg/Library/BaseFdtLib/libfdt/libfdt'
FIELDS = ['schema', 'x0_fdt', 'x1', 'x2', 'x3', 'lr', 'sp', 'current_el', 'sctlr',
          'daif', 'cntfrq', 'cntpct', 'mpidr', 'probe_base', 'image_base',
          'original_entry_offset', 'original_image_size', 'fdt_copy',
          'probe_extent', 'probe_end']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def align(value, size):
    return (value + size - 1) // size * size


def run(out, command):
    path = out / 'commands.json'
    records = json.loads(path.read_text()) if path.exists() else []
    result = subprocess.run([str(x) for x in command], capture_output=True)
    records.append(dict(command=[str(x) for x in command], returncode=result.returncode))
    path.write_text(json.dumps(records, indent=2) + '\n')
    with (out / 'build.log').open('ab') as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result.stdout


def image_parameters(image):
    assert image[56:60] == b'ARM\x64'
    instruction, second = struct.unpack_from('<II', image)
    assert instruction & 0xfc000000 == 0x14000000 and second == 0, 'Only direct B-entry Image accepted'
    displacement = instruction & 0x3ffffff
    if displacement & 0x2000000:
        displacement -= 0x4000000
    entry = displacement * 4
    offset, size, flags = struct.unpack_from('<QQQ', image, 8)
    assert 64 <= entry < len(image) and 64 <= len(image) <= size
    assert offset < 0x200000 and offset % 4096 == 0 and flags & 1 == 0
    return dict(instruction=instruction, entry=entry, text_offset=offset, image_size=size,
                probe_offset=align(size, 65536))


def compile_probe(out, parameters, identifier, main_source=None, extra_defines=()):
    defines = [f'-DPROBE_OFFSET={parameters["probe_offset"]}',
               f'-DORIGINAL_ENTRY_OFFSET={parameters["entry"]}',
               f'-DORIGINAL_IMAGE_SIZE={parameters["image_size"]}ULL',
               f'-DORIGINAL_INSTRUCTION={parameters["instruction"]}U',
               '-DPROBE_ID="' + identifier + '"']
    flags = ['-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
             '-fno-asynchronous-unwind-tables', '-fno-unwind-tables', '-fpie',
             '-fvisibility=hidden', '-mgeneral-regs-only', '-mstrict-align',
             '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror',
             '-I' + str(LIBFDT)]
    defines += list(extra_defines)
    inputs = [SOURCE / 'EntryProbe.S', main_source or SOURCE / 'EntryProbe.c', SOURCE / 'Runtime.c']
    inputs += [LIBFDT / (name + '.c') for name in ['fdt', 'fdt_ro', 'fdt_rw', 'fdt_wip']]
    compiler = Path(subprocess.check_output(['which', 'aarch64-linux-gnu-gcc'], text=True).strip()).resolve()
    provenance = dict(inputs=[dict(file=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))
                              for path in dict.fromkeys([*inputs, SOURCE / 'EntryProbe.c', SOURCE / 'EntryProbe.ld', LIBFDT / 'libfdt.h'])],
                      compiler_version=subprocess.check_output([str(compiler), '--version'], text=True),
                      compiler_sha256=sha(compiler.read_bytes()),
                      libfdt_revision=subprocess.check_output(['git', '-C', str(LIBFDT), 'rev-parse', 'HEAD'], text=True).strip(),
                      identifier=identifier, parameters=parameters)
    (out / 'probe-inputs.json').write_text(json.dumps(provenance, indent=2) + '\n')
    objects = []
    for i, source in enumerate(inputs):
        obj = out / f'probe-{i}.o'
        run(out, ['aarch64-linux-gnu-gcc', *flags, *defines, '-c', source, '-o', obj])
        objects.append(obj)
    elf = out / 'EntryProbe.elf'
    run(out, ['aarch64-linux-gnu-gcc', '-nostdlib', '-static', '-no-pie',
              '-Wl,--build-id=none,--gc-sections,-T,' + str(SOURCE / 'EntryProbe.ld'),
              '-o', elf, *objects])
    relocations = run(out, ['aarch64-linux-gnu-readelf', '-r', elf]).decode()
    assert 'There are no relocations' in relocations
    run(out, ['aarch64-linux-gnu-objcopy', '-O', 'binary', elf, out / 'EntryProbe.bin'])
    (out / 'EntryProbe.disassembly.txt').write_bytes(run(out, ['aarch64-linux-gnu-objdump', '-d', elf]))
    payload = (out / 'EntryProbe.bin').read_bytes()
    assert len(payload) <= 2 * 1024 * 1024
    return payload


def instrument(image, payload, parameters):
    start = parameters['probe_offset']
    result = bytearray(image)
    result.extend(bytes(start - len(result)))
    result.extend(payload)
    result.extend(bytes(align(len(result), 4096) - len(result)))
    assert start < 128 * 1024 * 1024
    struct.pack_into('<I', result, 0, 0x14000000 | (start // 4))
    struct.pack_into('<Q', result, 16, len(result))
    # Exact input bytes remain unchanged except the two documented fields.
    restored = bytearray(result[:len(image)])
    struct.pack_into('<I', restored, 0, parameters['instruction'])
    struct.pack_into('<Q', restored, 16, parameters['image_size'])
    assert restored == image
    return bytes(result)
