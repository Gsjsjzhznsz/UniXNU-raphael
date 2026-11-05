/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef RAPHAEL_ANDROID_RETURN_WIRE_H
#define RAPHAEL_ANDROID_RETURN_WIRE_H
#define RPH_RETURN_POLICY_MAGIC 0x3130544552485052ULL /* RPHRET01 */
#define RPH_RETURN_STATE_VERSION 2U
#define RPH_RETURN_STATE_MAGIC 0x3130545352485052ULL /* RPHRST01 */
#define RPH_RETURN_TAIL_BYTES 0x40000U
#define RPH_RETURN_STUB_MAX 0x20000U
#define RPH_RETURN_SCRATCH_BYTES 65536U
struct rph_return_policy {
 unsigned long long Magic,Version,RamdiskBytes,SourceBytes,KernelBytes,KernelImageBytes;
 unsigned long long EntryOffset,ImageInstruction,SourceCrc,KernelCrc,RamdiskCrc,Conduit;
};
struct rph_return_state {
 unsigned long long Magic,Version,Fdt,Output,KernelBytes,ImageBytes,Entry,Source,SourceBytes;
 unsigned long long SourceCrc,KernelCrc,Wire,LowBase,LowEnd,HighBase,HighEnd;
 unsigned long long Arch[19];
 unsigned long long Conduit,ActualSourceCrc,ActualKernelCrc,DecodedBytes,DecoderStatus,Armed;
 unsigned long long AuxBase,AuxEnd;
};
#endif
