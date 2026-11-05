// SPDX-License-Identifier: BSD-2-Clause-Patent
#ifndef RAPHAEL_PAYLOAD_FIXTURE_H
#define RAPHAEL_PAYLOAD_FIXTURE_H
#include <Uefi.h>
#define FIXTURE_GUID {0xf34ab01d,0xc94c,0x4a33,{0x89,0x57,0xc5,0x58,0x94,0x9c,0x64,0xdf}}
#define FIXTURE_MAGIC 0x5241504850524f42ULL
typedef struct {UINT64 Magic,Calls,OptionsOk,ParentOk;EFI_HANDLE Parent;} FIXTURE_RESULT;
#endif
