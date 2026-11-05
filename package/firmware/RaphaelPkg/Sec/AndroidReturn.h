// SPDX-License-Identifier: BSD-2-Clause-Patent
#include <RaphaelAndroidReturn.h>
#include <RaphaelDiagnostic.h>
#include <Library/ArmMmuLib.h>
#include <Library/RaphaelMemoryContractLib.h>
BOOLEAN RaphaelPrepareAndroidReturn(RAPHAEL_DIAGNOSTIC *,CONST VOID *,CONST RAPHAEL_RANGE *,UINTN,CONST RAPHAEL_RANGE *,UINTN);
BOOLEAN RaphaelMapAndroidOutput(ARM_MEMORY_REGION_DESCRIPTOR *);
BOOLEAN RaphaelMapAndroidReturn(ARM_MEMORY_REGION_DESCRIPTOR *);
BOOLEAN RaphaelArmAndroidReturnEarly(RAPHAEL_DIAGNOSTIC *);
BOOLEAN RaphaelArmAndroidReturn(RAPHAEL_DIAGNOSTIC *);
BOOLEAN RaphaelExportAndroidReturn(VOID *);
VOID RaphaelFinishAndroidReturn(RAPHAEL_DIAGNOSTIC *);
