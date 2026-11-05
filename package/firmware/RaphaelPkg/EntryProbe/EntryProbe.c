/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include <stdint.h>
#include <stddef.h>
#include <libfdt.h>

extern unsigned char probe_fdt[] __attribute__((visibility("hidden")));
extern unsigned char probe_storage_end[] __attribute__((visibility("hidden")));
extern unsigned char _probe_start[] __attribute__((visibility("hidden")));

/* Order is shared with EntryProbe.S and the readback decoder. */
struct entry_state {
  uint64_t x0, x1, x2, x3, lr, sp, current_el, sctlr;
  uint64_t daif, cntfrq, cntpct, mpidr, probe_base, image_base;
};

void *EntryProbeMain(const struct entry_state *s)
{
  const void *original = (const void *)(uintptr_t)s->x0;
  void *result = (void *)original;
  fdt64_t record[20];
  int chosen;
  size_t bytes = (size_t)(probe_storage_end - probe_fdt);
  uint64_t extent = (uintptr_t)probe_storage_end - (uintptr_t)_probe_start;

  /* No source tree is changed. Failure leaves the original FDT in use. */
  if ((s->x0 & 7) || fdt_check_header(original) ||
      fdt_totalsize(original) > bytes - 4096 ||
      fdt_open_into(original, probe_fdt, (int)bytes))
    goto out;
  chosen = fdt_path_offset(probe_fdt, "/chosen");
  if (chosen < 0)
    goto out;

  record[0] = cpu_to_fdt64(1); /* schema */
  record[1] = cpu_to_fdt64(s->x0);
  record[2] = cpu_to_fdt64(s->x1);
  record[3] = cpu_to_fdt64(s->x2);
  record[4] = cpu_to_fdt64(s->x3);
  record[5] = cpu_to_fdt64(s->lr);
  record[6] = cpu_to_fdt64(s->sp);
  record[7] = cpu_to_fdt64(s->current_el);
  record[8] = cpu_to_fdt64(s->sctlr);
  record[9] = cpu_to_fdt64(s->daif);
  record[10] = cpu_to_fdt64(s->cntfrq);
  record[11] = cpu_to_fdt64(s->cntpct);
  record[12] = cpu_to_fdt64(s->mpidr);
  record[13] = cpu_to_fdt64(s->probe_base);
  record[14] = cpu_to_fdt64(s->image_base);
  record[15] = cpu_to_fdt64(ORIGINAL_ENTRY_OFFSET);
  record[16] = cpu_to_fdt64(ORIGINAL_IMAGE_SIZE);
  record[17] = cpu_to_fdt64((uintptr_t)probe_fdt);
  record[18] = cpu_to_fdt64(extent);
  record[19] = cpu_to_fdt64((uintptr_t)probe_storage_end);

  if (fdt_setprop(probe_fdt, chosen, "raphael,entry-probe", record, sizeof(record)) ||
      fdt_setprop_string(probe_fdt, chosen, "raphael,entry-probe-id", PROBE_ID) ||
      fdt_add_mem_rsv(probe_fdt, s->probe_base, extent) || fdt_pack(probe_fdt))
    goto out;
  result = probe_fdt;
out:
  /* Keep the Android kernel's own header intact after instrumentation. */
  *(volatile uint32_t *)(uintptr_t)s->image_base = ORIGINAL_INSTRUCTION;
  *(volatile uint64_t *)(uintptr_t)(s->image_base + 16) = ORIGINAL_IMAGE_SIZE;
  __asm__ volatile("dsb sy\n\tdc cvac, %0\n\tdsb sy\n\tic ivau, %0\n\tdsb sy\n\tisb"
                   : : "r"(s->image_base) : "memory");
  return result;
}
