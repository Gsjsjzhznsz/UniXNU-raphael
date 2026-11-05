// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_NATIVE_EARLY_H
#define RAPHAEL_NATIVE_EARLY_H
#include <Uefi.h>
typedef struct { UINT64 Virtual,Bytes,FileBytes,Crc; } RAPHAEL_NATIVE_EARLY_RANGE;
typedef struct {
 UINT64 Magic,Version,Checkpoint,Opcode,ReturnVa,FrameBytes,ConstArgs,BootArgs,ArgsBytes,Count,BackupBytes,DeltaCapacity,Flags,Reserved[3];
 RAPHAEL_NATIVE_EARLY_RANGE Ranges[8];
} RAPHAEL_NATIVE_EARLY_POLICY;
typedef struct { UINT64 Virtual,Physical,Bytes,CrcBefore,CrcAfter,CrcRestored,ChangedWords,BackupOk; } RAPHAEL_NATIVE_EARLY_RANGE_RESULT;
typedef struct {
 UINT64 Version,Status,Error,CheckpointVa,ReturnVa,ConstArgsVa,OriginalArgsPa,ArgsBytes,BackupBase,BackupBytes,DeltaBytes,DeltaWords,DeltaOverflow,SavedRanges,RestoredRanges,ArgsCopyOk;
 RAPHAEL_NATIVE_EARLY_RANGE_RESULT Ranges[8];
} RAPHAEL_NATIVE_EARLY_RESULT;
typedef struct { UINT64 BaseOffset,TopOffset,SizeVa,ContextBytes; } RAPHAEL_NATIVE_THREAD_POLICY;
typedef struct {
 UINT64 Version,Status,ThreadVa,ThreadPa,BaseFieldPa,TopFieldPa,StackBase,StackTop,StackBytes,StackPages,FirstPa,LastPa;
} RAPHAEL_NATIVE_THREAD_RESULT;
typedef struct { UINT64 Version,Status,FieldVa,FieldPa,Top,Bytes,FirstPa,LastPa; } RAPHAEL_NATIVE_EXCEPTION_RESULT;
typedef struct { RAPHAEL_NATIVE_EARLY_RESULT Result; UINT64 Delta; RAPHAEL_NATIVE_THREAD_RESULT Thread; RAPHAEL_NATIVE_EXCEPTION_RESULT Exception; } RAPHAEL_NATIVE_EARLY_STATE;
typedef struct { UINT64 Config,Relay,Body,Bytes; } RAPHAEL_NATIVE_COMPILED_POLICY;
CONST RAPHAEL_NATIVE_COMPILED_POLICY *RaphaelNativeCompiledPolicy(VOID);
BOOLEAN RaphaelNativeEarlyExceptionStack(UINT64 Sp);
BOOLEAN RaphaelNativeEarlyStack(UINT64 Thread,UINT64 Sp,UINT64 Continuation);
EFI_STATUS RaphaelPrepareNativeEarly(VOID);
EFI_STATUS RaphaelSaveNativeEarly(UINT64 Args);
BOOLEAN RaphaelRestoreNativeEarly(VOID);
BOOLEAN RaphaelNativeEarlyArgs(UINT64 X0,UINT64 X1,UINT64 Args);
UINT64 RaphaelNativeEarlyCheckpoint(VOID);
UINT64 RaphaelNativeEarlyOpcode(VOID);
UINT64 RaphaelNativeEarlyReturn(VOID);
UINT64 RaphaelNativeEarlyFrame(VOID);
UINT64 RaphaelNativeEarlyState(VOID);
UINT64 RaphaelNativePlatformStop(VOID);
VOID RaphaelArmNativePanics(VOID);
#endif
