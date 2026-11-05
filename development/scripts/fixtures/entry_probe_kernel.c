/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <libfdt.h>

static volatile uint32_t *uart;
static int failures;
static void text(const char *s) { while (*s) *uart = (unsigned char)*s++; }
static void check(int good, const char *name)
{
  text(good ? "PASS " : "FAIL "); text(name); text("\n");
  if (!good) ++failures;
}

void fixture_main(const void *fdt, const unsigned char *image)
{
  int node, len;
  const fdt32_t *reg;
  const fdt64_t *record;
  const char *id, *args;
  uint64_t base, size;
  node = fdt_node_offset_by_compatible(fdt, -1, "arm,pl011");
  reg = fdt_getprop(fdt, node, "reg", &len);
  if (!reg || len < 16) for (;;) __asm__ volatile("wfe");
  uart = (volatile uint32_t *)(uintptr_t)(((uint64_t)fdt32_to_cpu(reg[0]) << 32) |
                                          fdt32_to_cpu(reg[1]));
  node = fdt_path_offset(fdt, "/chosen");
  record = fdt_getprop(fdt, node, "raphael,entry-probe", &len);
  check(record && len == 160, "probe property");
  id = fdt_getprop(fdt, node, "raphael,entry-probe-id", NULL);
  check(id && strcmp(id, "qemu-entry-probe-fixture") == 0, "probe identifier");
  args = fdt_getprop(fdt, node, "bootargs", NULL);
  check(args && strcmp(args, "fixture_cookie=unchanged") == 0, "original bootargs unchanged");
  if (record && len == 160) {
    uint64_t el = fdt64_to_cpu(record[7]);
    uint64_t sctlr = fdt64_to_cpu(record[8]);
    uint64_t probe_base = fdt64_to_cpu(record[13]);
    uint64_t extent = fdt64_to_cpu(record[18]);
    int found = 0;
    check(fdt64_to_cpu(record[0]) == 1, "record schema");
    check(el == 4 || el == 8, "entry exception level");
    check((sctlr & 5) == 0, "MMU and data cache off");
    check(fdt64_to_cpu(record[2]) == 0 && fdt64_to_cpu(record[3]) == 0 &&
          fdt64_to_cpu(record[4]) == 0, "reserved entry registers");
    check(fdt64_to_cpu(record[10]) != 0, "counter frequency");
    check(fdt64_to_cpu(record[14]) == (uintptr_t)image, "original kernel stayed in place");
    check(fdt64_to_cpu(record[17]) == (uintptr_t)fdt, "FDT clone handed off");
    check(fdt64_to_cpu(record[1]) != (uintptr_t)fdt, "source FDT kept separate");
    check(*(const uint64_t *)(image + 16) == fdt64_to_cpu(record[16]), "Image size restored");
    check(*(const uint32_t *)image == 0x14000010, "entry instruction restored");
    for (int i = 0; i < fdt_num_mem_rsv(fdt); ++i) {
      if (!fdt_get_mem_rsv(fdt, i, &base, &size) && base == probe_base && size == extent) found = 1;
    }
    check(found, "probe and copied FDT reserved");
  }
  text(failures ? "ENTRY_PROBE_FIXTURE_FAILED\n" : "ENTRY_PROBE_FIXTURE_OK\n");
  /* Emulator-only semihosting exit; no handset reset behavior is tested. */
  uint64_t status[2] = {0x20026, (uint64_t)failures};
  register uint64_t function __asm__("x0") = 0x20;
  register void *argument __asm__("x1") = status;
  __asm__ volatile("hlt #0xf000" : "+r"(function), "+r"(argument) : : "memory");
  for (;;) __asm__ volatile("wfe");
}
