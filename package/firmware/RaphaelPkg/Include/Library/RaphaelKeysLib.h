// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_KEYS_LIB_H
#define RAPHAEL_KEYS_LIB_H
#include <Base.h>
#include <RaphaelInputProbe.h>
#define RAPHAEL_KEY_REGISTER_COUNT 6
#define RAPHAEL_KEY_UP 1
#define RAPHAEL_KEY_DOWN 2
#define RAPHAEL_KEY_POWER 4
typedef struct { UINT64 Sid, Address, Observer, Command, Completion, Polls, Value, Error; } RAPHAEL_KEY_REGISTER;
typedef struct {
  UINT64 Version, Status, Transactions, Completed, Start, End, TimeoutTicks, Error;
  RAPHAEL_KEY_REGISTER Registers[RAPHAEL_KEY_REGISTER_COUNT];
} RAPHAEL_KEY_RESULT;
typedef struct { UINT64 PonObserver, VolumeObserver;UINT32 PonSid,PonAddress,VolumeSid,VolumeAddress,Frequency; } RAPHAEL_KEY_TRANSPORT;
typedef VOID (*RAPHAEL_KEY_WRITE32)(UINT64 Address,UINT32 Value,VOID *Context);
typedef UINT64 (*RAPHAEL_KEY_COUNTER)(VOID *Context);
BOOLEAN RaphaelKeyTransport(CONST RAPHAEL_INPUT_SNAPSHOT *Input,UINT32 Frequency,RAPHAEL_KEY_TRANSPORT *Transport);
VOID RaphaelCollectKeyRegisters(CONST RAPHAEL_INPUT_SNAPSHOT *Input,UINT32 Frequency,RAPHAEL_KEY_RESULT *Out,
  RAPHAEL_INPUT_READ32 Read,RAPHAEL_KEY_WRITE32 Write,RAPHAEL_KEY_COUNTER Counter,VOID *Context);
// Only RT_STS on the two validated peripherals is polled; no arbitrary PMIC API.
BOOLEAN RaphaelReadKeyState(CONST RAPHAEL_KEY_TRANSPORT *Transport,UINT32 *Keys,
  RAPHAEL_INPUT_READ32 Read,RAPHAEL_KEY_WRITE32 Write,RAPHAEL_KEY_COUNTER Counter,VOID *Context);

// Polling filter: one press event, no repeat, suppress held-at-entry and chords.
typedef struct {
  UINT64 Since, DebounceTicks;
  UINT32 Candidate, Stable, Initialized, Armed, PressedMask, ReleasedMask;
} RAPHAEL_KEY_FILTER;
UINT32 RaphaelFilterKeys(RAPHAEL_KEY_FILTER *Filter,UINT32 Raw,UINT64 Now);
BOOLEAN RaphaelKeyRegistersReady(CONST RAPHAEL_KEY_RESULT *Result);
#endif
