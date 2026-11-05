# SPDX-License-Identifier: BSD-2-Clause-Patent
# Isolated SEC/DXE diagnostic. Every placement is supplied by a generated layout.
# No default handset addresses. Native payload/loader support is opt-in.
[Defines]
!ifndef RAPHAEL_UFS_WRITE_PROBE
  DEFINE RAPHAEL_UFS_WRITE_PROBE = FALSE
!endif
!ifndef RAPHAEL_UFS_PAYLOAD
  DEFINE RAPHAEL_UFS_PAYLOAD = FALSE
!endif
!ifndef RAPHAEL_NATIVE_FAT_BYTES
  DEFINE RAPHAEL_NATIVE_FAT_BYTES = 20971520
!endif
!ifndef RAPHAEL_UFS_EXTENTS
  DEFINE RAPHAEL_UFS_EXTENTS = FALSE
!endif
!ifndef RAPHAEL_UFS_READ_LBA
  DEFINE RAPHAEL_UFS_READ_LBA = 0
!endif
!ifndef RAPHAEL_UFS_RESET_ON_ERROR
  DEFINE RAPHAEL_UFS_RESET_ON_ERROR = FALSE
!endif
!ifndef RAPHAEL_UFS_QUERY_ONLY
  DEFINE RAPHAEL_UFS_QUERY_ONLY = FALSE
!endif
!ifndef RAPHAEL_UFS_READ
  DEFINE RAPHAEL_UFS_READ = FALSE
!endif
!ifndef RAPHAEL_UFS_HANDOFF
  DEFINE RAPHAEL_UFS_HANDOFF = FALSE
!endif
!ifndef RAPHAEL_NATIVE_VIDEO
  DEFINE RAPHAEL_NATIVE_VIDEO = FALSE
!endif
!ifndef RAPHAEL_NATIVE_WATCHDOG_SECONDS
  DEFINE RAPHAEL_NATIVE_WATCHDOG_SECONDS = 20
!endif
!ifndef RAPHAEL_NATIVE_WATCHDOG_BASE
  DEFINE RAPHAEL_NATIVE_WATCHDOG_BASE = 0
  DEFINE RAPHAEL_NATIVE_WATCHDOG_HZ = 0
!endif
!ifndef RAPHAEL_NATIVE_KALLOC_ZONES
  DEFINE RAPHAEL_NATIVE_KALLOC_ZONES = 0
!endif
!ifndef RAPHAEL_NATIVE_PLATFORM_TEST
  DEFINE RAPHAEL_NATIVE_PLATFORM_TEST = FALSE
!endif
!ifndef RAPHAEL_SPARSE_ARENA
  DEFINE RAPHAEL_SPARSE_ARENA = FALSE
!endif
!ifndef RAPHAEL_DOWNLOADED_END
  DEFINE RAPHAEL_DOWNLOADED_END = 0
!endif
!ifndef RAPHAEL_STAGING_KERNEL_BYTES
  DEFINE RAPHAEL_STAGING_KERNEL_BYTES = 0
!endif
!ifndef RAPHAEL_STAGING_KERNEL_CRC
  DEFINE RAPHAEL_STAGING_KERNEL_CRC = 0
!endif
!ifndef RAPHAEL_ANDROID_RETURN
  DEFINE RAPHAEL_ANDROID_RETURN = FALSE
!endif
!ifndef RAPHAEL_ANDROID_RETURN_QEMU
  DEFINE RAPHAEL_ANDROID_RETURN_QEMU = FALSE
!endif
!ifndef RAPHAEL_NATIVE_MMU_TEST
  DEFINE RAPHAEL_NATIVE_MMU_TEST = FALSE
!endif
!ifndef RAPHAEL_NATIVE_PMAP_TEST
  DEFINE RAPHAEL_NATIVE_PMAP_TEST = FALSE
!endif
!ifndef RAPHAEL_NATIVE_EARLY_TEST
  DEFINE RAPHAEL_NATIVE_EARLY_TEST = FALSE
!endif
!ifndef RAPHAEL_NATIVE_ENTRY_TEST
  DEFINE RAPHAEL_NATIVE_ENTRY_TEST = FALSE
!endif
!ifndef RAPHAEL_NATIVE_EXIT_COMPLETE
  DEFINE RAPHAEL_NATIVE_EXIT_COMPLETE = FALSE
!endif
!ifndef RAPHAEL_NATIVE_LOAD_TEST
  DEFINE RAPHAEL_NATIVE_LOAD_TEST = FALSE
!endif
!ifndef RAPHAEL_NATIVE_HANDOFF
  DEFINE RAPHAEL_NATIVE_HANDOFF = FALSE
!endif
!ifndef RAPHAEL_NATIVE_BOOT
  DEFINE RAPHAEL_NATIVE_BOOT = FALSE
!endif
!ifndef RAPHAEL_NATIVE_QEMU_GATE
  DEFINE RAPHAEL_NATIVE_QEMU_GATE = FALSE
!endif
!ifndef RAPHAEL_FD_BLOCKS
  DEFINE RAPHAEL_FD_BLOCKS = 0x300
!endif
!ifndef RAPHAEL_KERNEL_WINDOW
  DEFINE RAPHAEL_KERNEL_WINDOW = FALSE
!endif
!ifndef RAPHAEL_RAM_CACHE_WRITE_PAGES
  DEFINE RAPHAEL_RAM_CACHE_WRITE_PAGES = 0
!endif
!ifndef RAPHAEL_RAM_MAPPED_PROBE
  DEFINE RAPHAEL_RAM_MAPPED_PROBE = FALSE
!endif
  PLATFORM_NAME = RaphaelDiagnostic
  PLATFORM_GUID = 71471C67-9CAC-444A-A00B-DA429A983B18
  PLATFORM_VERSION = 0.1
  DSC_SPECIFICATION = 0x0001001C
  OUTPUT_DIRECTORY = Build/RaphaelDiagnostic
  SUPPORTED_ARCHITECTURES = AARCH64
  BUILD_TARGETS = DEBUG
  SKUID_IDENTIFIER = DEFAULT
  FLASH_DEFINITION = RaphaelPkg/Diagnostic.fdf
!ifndef RAPHAEL_STOP_AFTER_STAGE
  DEFINE RAPHAEL_STOP_AFTER_STAGE = 4
!endif
!ifndef RAPHAEL_DISPLAY_PROBE
  DEFINE RAPHAEL_DISPLAY_PROBE = FALSE
!endif
!ifndef RAPHAEL_SMMU_PROBE
  DEFINE RAPHAEL_SMMU_PROBE = FALSE
!endif
!ifndef RAPHAEL_PIXEL_PROBE
  DEFINE RAPHAEL_PIXEL_PROBE = FALSE
!endif
!ifndef RAPHAEL_PIXEL_WRITE
  DEFINE RAPHAEL_PIXEL_WRITE = FALSE
!endif
!ifndef RAPHAEL_EXPERIMENTAL_GOP
  DEFINE RAPHAEL_EXPERIMENTAL_GOP = FALSE
!endif
!ifndef RAPHAEL_INPUT_PROBE
  DEFINE RAPHAEL_INPUT_PROBE = FALSE
!endif
!ifndef RAPHAEL_INPUT_READ
  DEFINE RAPHAEL_INPUT_READ = FALSE
!endif
!ifndef RAPHAEL_INPUT_PROTOCOL
  DEFINE RAPHAEL_INPUT_PROTOCOL = FALSE
!endif
!ifndef RAPHAEL_MENU_TEST
  DEFINE RAPHAEL_MENU_TEST = FALSE
!endif
!ifndef RAPHAEL_PAYLOAD_TEST
  DEFINE RAPHAEL_PAYLOAD_TEST = FALSE
!endif
!ifndef RAPHAEL_DARWIN_TEST
  DEFINE RAPHAEL_DARWIN_TEST = FALSE
!endif
!ifndef RAPHAEL_QEMU_ARCH_TEST
  DEFINE RAPHAEL_QEMU_ARCH_TEST = FALSE
!endif
!ifndef RAPHAEL_GIC_PROBE
  DEFINE RAPHAEL_GIC_PROBE = FALSE
!endif
!ifndef RAPHAEL_ICC_PROBE
  DEFINE RAPHAEL_ICC_PROBE = FALSE
!endif
!ifndef RAPHAEL_ICC_FAULT_TEST
  DEFINE RAPHAEL_ICC_FAULT_TEST = FALSE
!endif
!include MdePkg/MdeLibs.dsc.inc

!ifndef RAPHAEL_TIMER_SOURCE_TEST
  DEFINE RAPHAEL_TIMER_SOURCE_TEST = FALSE
!endif

!ifndef RAPHAEL_PPI_ENABLE_PROBE
  DEFINE RAPHAEL_PPI_ENABLE_PROBE = FALSE
!endif

!ifndef RAPHAEL_GIC_ENABLE_MAP
  DEFINE RAPHAEL_GIC_ENABLE_MAP = FALSE
!endif

!ifndef RAPHAEL_TIMER_ROUTE_TEST
  DEFINE RAPHAEL_TIMER_ROUTE_TEST = FALSE
!endif

!ifndef RAPHAEL_TIMER_ROUTE_FAULT_TEST
  DEFINE RAPHAEL_TIMER_ROUTE_FAULT_TEST = FALSE
!endif

!ifndef RAPHAEL_PHYSICAL_TIMER_ARCH
  DEFINE RAPHAEL_PHYSICAL_TIMER_ARCH = FALSE
!endif

!ifndef RAPHAEL_TIMER_IRQ_TEST
  DEFINE RAPHAEL_TIMER_IRQ_TEST = FALSE
!endif

!ifndef RAPHAEL_RAM_WRITE_PAGES
  DEFINE RAPHAEL_RAM_WRITE_PAGES = 0
!endif

!ifndef RAPHAEL_RAM_READ_PROBE
  DEFINE RAPHAEL_RAM_READ_PROBE = FALSE
!endif

!ifndef RAPHAEL_MANAGER_KEYS
  DEFINE RAPHAEL_MANAGER_KEYS = FALSE
!endif
!ifndef RAPHAEL_VISIBLE_MANAGER
  DEFINE RAPHAEL_VISIBLE_MANAGER = FALSE
!endif

[LibraryClasses]
  SemihostLib|ArmPkg/Library/SemihostLib/SemihostLib.inf
  RaphaelRamWriteLib|RaphaelPkg/Library/RaphaelRamWriteLib/RaphaelRamWriteLib.inf
  RaphaelManagerUiLib|RaphaelPkg/Library/RaphaelManagerUiLib/RaphaelManagerUiLib.inf
  BaseLib|MdePkg/Library/BaseLib/BaseLib.inf
  BaseMemoryLib|MdePkg/Library/BaseMemoryLib/BaseMemoryLib.inf
  PcdLib|MdePkg/Library/BasePcdLibNull/BasePcdLibNull.inf
  PrintLib|MdePkg/Library/BasePrintLib/BasePrintLib.inf
  DebugLib|RaphaelPkg/Library/RaphaelDiagnosticDebugLib/RaphaelDiagnosticDebugLib.inf
  ArmLib|MdePkg/Library/ArmLib/ArmBaseLib.inf
  CacheMaintenanceLib|ArmPkg/Library/ArmCacheMaintenanceLib/ArmCacheMaintenanceLib.inf
  ArmMmuLib|UefiCpuPkg/Library/ArmMmuLib/ArmMmuBaseLib.inf
  FdtLib|MdePkg/Library/BaseFdtLib/BaseFdtLib.inf
  PrePiLib|EmbeddedPkg/Library/PrePiLib/PrePiLib.inf
  PrePiHobListPointerLib|ArmPlatformPkg/Library/PrePiHobListPointerLib/PrePiHobListPointerLib.inf
  PeCoffLib|MdePkg/Library/BasePeCoffLib/BasePeCoffLib.inf
  PeCoffExtraActionLib|MdePkg/Library/BasePeCoffExtraActionLibNull/BasePeCoffExtraActionLibNull.inf
  PeCoffGetEntryPointLib|MdePkg/Library/BasePeCoffGetEntryPointLib/BasePeCoffGetEntryPointLib.inf
  UefiDecompressLib|MdePkg/Library/BaseUefiDecompressLib/BaseUefiDecompressLib.inf
  ExtractGuidedSectionLib|MdePkg/Library/BaseExtractGuidedSectionLib/BaseExtractGuidedSectionLib.inf
  PerformanceLib|MdePkg/Library/BasePerformanceLibNull/BasePerformanceLibNull.inf
  SerialPortLib|MdePkg/Library/BaseSerialPortLibNull/BaseSerialPortLibNull.inf
  TimerLib|ArmPkg/Library/ArmArchTimerLib/ArmArchTimerLib.inf
  ArmGenericTimerCounterLib|ArmPkg/Library/ArmGenericTimerPhyCounterLib/ArmGenericTimerPhyCounterLib.inf
  DebugAgentLib|MdeModulePkg/Library/DebugAgentLibNull/DebugAgentLibNull.inf
  ReportStatusCodeLib|MdePkg/Library/BaseReportStatusCodeLibNull/BaseReportStatusCodeLibNull.inf
  UefiLib|MdePkg/Library/UefiLib/UefiLib.inf
  UefiBootServicesTableLib|MdePkg/Library/UefiBootServicesTableLib/UefiBootServicesTableLib.inf
  UefiRuntimeServicesTableLib|MdePkg/Library/UefiRuntimeServicesTableLib/UefiRuntimeServicesTableLib.inf
  DevicePathLib|MdePkg/Library/UefiDevicePathLib/UefiDevicePathLib.inf
  DxeServicesLib|MdePkg/Library/DxeServicesLib/DxeServicesLib.inf
  DxeServicesTableLib|MdePkg/Library/DxeServicesTableLib/DxeServicesTableLib.inf
  DxeCoreEntryPoint|MdePkg/Library/DxeCoreEntryPoint/DxeCoreEntryPoint.inf
  UefiApplicationEntryPoint|MdePkg/Library/UefiApplicationEntryPoint/UefiApplicationEntryPoint.inf
  UefiDriverEntryPoint|MdePkg/Library/UefiDriverEntryPoint/UefiDriverEntryPoint.inf
  CpuExceptionHandlerLib|MdeModulePkg/Library/CpuExceptionHandlerLibNull/CpuExceptionHandlerLibNull.inf
  ImagePropertiesRecordLib|MdeModulePkg/Library/ImagePropertiesRecordLib/ImagePropertiesRecordLib.inf
  DxeMemoryProtectionHobLib|MdeModulePkg/Library/MemoryProtectionHobLib/DxeMemoryProtectionHobLib.inf
  RaphaelMemoryContractLib|RaphaelPkg/Library/RaphaelMemoryContractLib/RaphaelMemoryContractLib.inf
  RaphaelFramebufferLib|RaphaelPkg/Library/RaphaelFramebufferLib/RaphaelFramebufferLib.inf
  UniXNULib|UniXNUPkg/Library/UniXNULib/UniXNULib.inf
  RaphaelKeysLib|RaphaelPkg/Library/RaphaelKeysLib/RaphaelKeysLib.inf
  RaphaelGopLib|RaphaelPkg/Library/RaphaelGopLib/RaphaelGopLib.inf
  FrameBufferBltLib|MdeModulePkg/Library/FrameBufferBltLib/FrameBufferBltLib.inf

[LibraryClasses.common.SEC]
  HobLib|EmbeddedPkg/Library/PrePiHobLib/PrePiHobLib.inf
  MemoryAllocationLib|EmbeddedPkg/Library/PrePiMemoryAllocationLib/PrePiMemoryAllocationLib.inf

[LibraryClasses.common.UEFI_APPLICATION]
  HobLib|MdePkg/Library/DxeHobLib/DxeHobLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf

[LibraryClasses.common.DXE_CORE]
  HobLib|MdePkg/Library/DxeCoreHobLib/DxeCoreHobLib.inf
  MemoryAllocationLib|MdeModulePkg/Library/DxeCoreMemoryAllocationLib/DxeCoreMemoryAllocationLib.inf

[LibraryClasses.common.DXE_DRIVER]
  HobLib|MdePkg/Library/DxeHobLib/DxeHobLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf

[LibraryClasses.common.UEFI_DRIVER]
  HobLib|MdePkg/Library/DxeHobLib/DxeHobLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf

[LibraryClasses.common.DXE_RUNTIME_DRIVER]
  HobLib|MdePkg/Library/DxeHobLib/DxeHobLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf

[PcdsFixedAtBuild]
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsPayload|$(RAPHAEL_UFS_PAYLOAD)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeFatBytes|$(RAPHAEL_NATIVE_FAT_BYTES)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsExtents|$(RAPHAEL_UFS_EXTENTS)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsReadLba|$(RAPHAEL_UFS_READ_LBA)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsResetOnError|$(RAPHAEL_UFS_RESET_ON_ERROR)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsQueryOnly|$(RAPHAEL_UFS_QUERY_ONLY)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsWriteProbe|$(RAPHAEL_UFS_WRITE_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsRead|$(RAPHAEL_UFS_READ)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsHandoff|$(RAPHAEL_UFS_HANDOFF)
  gRaphaelTokenSpaceGuid.PcdRaphaelSparseArena|$(RAPHAEL_SPARSE_ARENA)
  gRaphaelTokenSpaceGuid.PcdRaphaelDownloadedEnd|$(RAPHAEL_DOWNLOADED_END)
  gRaphaelTokenSpaceGuid.PcdRaphaelStagingKernelBytes|$(RAPHAEL_STAGING_KERNEL_BYTES)
  gRaphaelTokenSpaceGuid.PcdRaphaelStagingKernelCrc|$(RAPHAEL_STAGING_KERNEL_CRC)
  gRaphaelTokenSpaceGuid.PcdRaphaelAndroidReturn|$(RAPHAEL_ANDROID_RETURN)
  gRaphaelTokenSpaceGuid.PcdRaphaelAndroidReturnQemu|$(RAPHAEL_ANDROID_RETURN_QEMU)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeMmuTest|$(RAPHAEL_NATIVE_MMU_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeEarlyTest|$(RAPHAEL_NATIVE_EARLY_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogBase|$(RAPHAEL_NATIVE_WATCHDOG_BASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogHz|$(RAPHAEL_NATIVE_WATCHDOG_HZ)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogSeconds|$(RAPHAEL_NATIVE_WATCHDOG_SECONDS)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeKallocZones|$(RAPHAEL_NATIVE_KALLOC_ZONES)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativePlatformTest|$(RAPHAEL_NATIVE_PLATFORM_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativePmapTest|$(RAPHAEL_NATIVE_PMAP_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeEntryTest|$(RAPHAEL_NATIVE_ENTRY_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeExitComplete|$(RAPHAEL_NATIVE_EXIT_COMPLETE)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeLoadTest|$(RAPHAEL_NATIVE_LOAD_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeVideo|$(RAPHAEL_NATIVE_VIDEO)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeHandoff|$(RAPHAEL_NATIVE_HANDOFF)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeBoot|$(RAPHAEL_NATIVE_BOOT)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeQemuGate|$(RAPHAEL_NATIVE_QEMU_GATE)
  gRaphaelTokenSpaceGuid.PcdRaphaelKernelWindow|$(RAPHAEL_KERNEL_WINDOW)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamCacheWritePages|$(RAPHAEL_RAM_CACHE_WRITE_PAGES)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamWritePages|$(RAPHAEL_RAM_WRITE_PAGES)
  gRaphaelTokenSpaceGuid.PcdRaphaelVisibleManager|$(RAPHAEL_VISIBLE_MANAGER)
  gRaphaelTokenSpaceGuid.PcdRaphaelManagerKeys|$(RAPHAEL_MANAGER_KEYS)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamMappedProbe|$(RAPHAEL_RAM_MAPPED_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamReadProbe|$(RAPHAEL_RAM_READ_PROBE)
  gEfiMdePkgTokenSpaceGuid.PcdDebugPropertyMask|0x03
  gEfiMdePkgTokenSpaceGuid.PcdFixedDebugPrintErrorLevel|0x80000042
  # Explicit scratch inside the downloaded bridge; no default 0x01000000 table.
  gEfiMdePkgTokenSpaceGuid.PcdGuidedExtractHandlerTableAddress|$(RAPHAEL_CONTEXTBASE) + 0xf000
  gEfiMdePkgTokenSpaceGuid.PcdMaximumGuidedExtractHandler|16
  gRaphaelTokenSpaceGuid.PcdRaphaelImageBase|$(RAPHAEL_IMAGEBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelImageSize|$(RAPHAEL_IMAGESIZE)
  gRaphaelTokenSpaceGuid.PcdRaphaelOriginalEntry|$(RAPHAEL_ORIGINALENTRY)
  gRaphaelTokenSpaceGuid.PcdRaphaelOriginalInstruction|$(RAPHAEL_ORIGINALINSTRUCTION)
  gRaphaelTokenSpaceGuid.PcdRaphaelExtentBase|$(RAPHAEL_EXTENTBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelExtentEnd|$(RAPHAEL_EXTENTEND)
  gRaphaelTokenSpaceGuid.PcdRaphaelFdBase|$(RAPHAEL_FDBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelFdSize|$(RAPHAEL_FDSIZE)
  gRaphaelTokenSpaceGuid.PcdRaphaelStackBase|$(RAPHAEL_STACKBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelStackSize|$(RAPHAEL_STACKSIZE)
  gRaphaelTokenSpaceGuid.PcdRaphaelArenaBase|$(RAPHAEL_ARENABASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelArenaSize|$(RAPHAEL_ARENASIZE)
  gRaphaelTokenSpaceGuid.PcdRaphaelFdtBase|$(RAPHAEL_FDTBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelFdtSize|$(RAPHAEL_FDTSIZE)
  gRaphaelTokenSpaceGuid.PcdRaphaelContextBase|$(RAPHAEL_CONTEXTBASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelTestId|"$(RAPHAEL_TEST_ID)"
  gRaphaelTokenSpaceGuid.PcdRaphaelStopAfterStage|$(RAPHAEL_STOP_AFTER_STAGE)
  gRaphaelTokenSpaceGuid.PcdRaphaelIccProbe|$(RAPHAEL_ICC_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelIccFaultTest|$(RAPHAEL_ICC_FAULT_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelTimerSourceTest|$(RAPHAEL_TIMER_SOURCE_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelPpiEnableProbe|$(RAPHAEL_PPI_ENABLE_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelTimerRouteFaultTest|$(RAPHAEL_TIMER_ROUTE_FAULT_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelPhysicalTimerArch|$(RAPHAEL_PHYSICAL_TIMER_ARCH)
  gRaphaelTokenSpaceGuid.PcdRaphaelTimerIrqTest|$(RAPHAEL_TIMER_IRQ_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelTimerRouteTest|$(RAPHAEL_TIMER_ROUTE_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelGicEnableMap|$(RAPHAEL_GIC_ENABLE_MAP)
  gRaphaelTokenSpaceGuid.PcdRaphaelGicProbe|$(RAPHAEL_GIC_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelDisplayProbe|$(RAPHAEL_DISPLAY_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelSmmuProbe|$(RAPHAEL_SMMU_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelPixelProbe|$(RAPHAEL_PIXEL_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelPixelWrite|$(RAPHAEL_PIXEL_WRITE)
  gRaphaelTokenSpaceGuid.PcdRaphaelExperimentalGop|$(RAPHAEL_EXPERIMENTAL_GOP)
  gRaphaelTokenSpaceGuid.PcdRaphaelInputProbe|$(RAPHAEL_INPUT_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelInputRead|$(RAPHAEL_INPUT_READ)
  gRaphaelTokenSpaceGuid.PcdRaphaelInputProtocol|$(RAPHAEL_INPUT_PROTOCOL)
  gRaphaelTokenSpaceGuid.PcdRaphaelMenuTest|$(RAPHAEL_MENU_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelPayloadTest|$(RAPHAEL_PAYLOAD_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelDarwinTest|$(RAPHAEL_DARWIN_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelQemuArchTest|$(RAPHAEL_QEMU_ARCH_TEST)

!if $(RAPHAEL_QEMU_ARCH_TEST) == TRUE || $(RAPHAEL_PHYSICAL_TIMER_ARCH) == TRUE
[LibraryClasses]
  SemihostLib|ArmPkg/Library/SemihostLib/SemihostLib.inf
  CpuLib|MdePkg/Library/BaseCpuLib/BaseCpuLib.inf
  SynchronizationLib|MdePkg/Library/BaseSynchronizationLib/BaseSynchronizationLib.inf
  IoLib|MdePkg/Library/BaseIoLibIntrinsic/BaseIoLibIntrinsic.inf
[PcdsFixedAtBuild]
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsExtents|$(RAPHAEL_UFS_EXTENTS)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsReadLba|$(RAPHAEL_UFS_READ_LBA)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsResetOnError|$(RAPHAEL_UFS_RESET_ON_ERROR)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsQueryOnly|$(RAPHAEL_UFS_QUERY_ONLY)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsWriteProbe|$(RAPHAEL_UFS_WRITE_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsRead|$(RAPHAEL_UFS_READ)
  gRaphaelTokenSpaceGuid.PcdRaphaelUfsHandoff|$(RAPHAEL_UFS_HANDOFF)
  gRaphaelTokenSpaceGuid.PcdRaphaelSparseArena|$(RAPHAEL_SPARSE_ARENA)
  gRaphaelTokenSpaceGuid.PcdRaphaelDownloadedEnd|$(RAPHAEL_DOWNLOADED_END)
  gRaphaelTokenSpaceGuid.PcdRaphaelStagingKernelBytes|$(RAPHAEL_STAGING_KERNEL_BYTES)
  gRaphaelTokenSpaceGuid.PcdRaphaelStagingKernelCrc|$(RAPHAEL_STAGING_KERNEL_CRC)
  gRaphaelTokenSpaceGuid.PcdRaphaelAndroidReturn|$(RAPHAEL_ANDROID_RETURN)
  gRaphaelTokenSpaceGuid.PcdRaphaelAndroidReturnQemu|$(RAPHAEL_ANDROID_RETURN_QEMU)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeMmuTest|$(RAPHAEL_NATIVE_MMU_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeEarlyTest|$(RAPHAEL_NATIVE_EARLY_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogBase|$(RAPHAEL_NATIVE_WATCHDOG_BASE)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogHz|$(RAPHAEL_NATIVE_WATCHDOG_HZ)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeWatchdogSeconds|$(RAPHAEL_NATIVE_WATCHDOG_SECONDS)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeKallocZones|$(RAPHAEL_NATIVE_KALLOC_ZONES)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativePlatformTest|$(RAPHAEL_NATIVE_PLATFORM_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativePmapTest|$(RAPHAEL_NATIVE_PMAP_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeEntryTest|$(RAPHAEL_NATIVE_ENTRY_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeExitComplete|$(RAPHAEL_NATIVE_EXIT_COMPLETE)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeLoadTest|$(RAPHAEL_NATIVE_LOAD_TEST)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeVideo|$(RAPHAEL_NATIVE_VIDEO)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeHandoff|$(RAPHAEL_NATIVE_HANDOFF)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeBoot|$(RAPHAEL_NATIVE_BOOT)
  gRaphaelTokenSpaceGuid.PcdRaphaelNativeQemuGate|$(RAPHAEL_NATIVE_QEMU_GATE)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamMappedProbe|$(RAPHAEL_RAM_MAPPED_PROBE)
  gRaphaelTokenSpaceGuid.PcdRaphaelRamReadProbe|$(RAPHAEL_RAM_READ_PROBE)
!if $(RAPHAEL_QEMU_ARCH_TEST) == TRUE
  gArmTokenSpaceGuid.PcdGicDistributorBase|$(RAPHAEL_QEMU_GICD)
  gArmTokenSpaceGuid.PcdGicRedistributorsBase|$(RAPHAEL_QEMU_GICR)
  gRaphaelTokenSpaceGuid.PcdRaphaelQemuGicDBytes|$(RAPHAEL_QEMU_GICD_BYTES)
  gRaphaelTokenSpaceGuid.PcdRaphaelQemuGicRBytes|$(RAPHAEL_QEMU_GICR_BYTES)
  gArmTokenSpaceGuid.PcdArmArchTimerSecIntrNum|$(RAPHAEL_QEMU_TIMER_SEC)
  gArmTokenSpaceGuid.PcdArmArchTimerIntrNum|$(RAPHAEL_QEMU_TIMER_PHYS)
  gArmTokenSpaceGuid.PcdArmArchTimerVirtIntrNum|$(RAPHAEL_QEMU_TIMER_VIRT)
  gArmTokenSpaceGuid.PcdArmArchTimerHypIntrNum|$(RAPHAEL_QEMU_TIMER_HYP)
  gEmbeddedTokenSpaceGuid.PcdTimerPeriod|100000
!endif
[PcdsFeatureFlag]
  gArmTokenSpaceGuid.PcdRemapUnusedMemoryNx|FALSE
[Components]
  ArmPkg/Drivers/CpuDxe/CpuDxe.inf {
    <LibraryClasses>
      CpuExceptionHandlerLib|UefiCpuPkg/Library/CpuExceptionHandlerLib/DxeCpuExceptionHandlerLib.inf
  }
!if $(RAPHAEL_QEMU_ARCH_TEST) == TRUE
  ArmPkg/Drivers/ArmGicDxe/ArmGicV3Dxe.inf
  ArmPkg/Drivers/TimerDxe/TimerDxe.inf
!else
  RaphaelPkg/Drivers/PhysicalTimerDxe/PhysicalTimerDxe.inf
!endif
!endif

!if $(RAPHAEL_DARWIN_TEST) == TRUE
[Components]
  DarwinBootPkg/Driver/DarwinBoot.inf
!endif

!if $(RAPHAEL_PAYLOAD_TEST) == TRUE
[Components]
  UniXNUPkg/Driver/UniXNURamDiskDxe/UniXNURamDiskDxe.inf
  MdeModulePkg/Universal/Disk/DiskIoDxe/DiskIoDxe.inf
  FatPkg/EnhancedFatDxe/Fat.inf
  MdeModulePkg/Universal/Disk/UnicodeCollation/EnglishDxe/EnglishDxe.inf
!endif

[Components]
  RaphaelPkg/Application/MenuFixture/MenuFixture.inf {
    <LibraryClasses>
      DebugLib|MdePkg/Library/BaseDebugLibNull/BaseDebugLibNull.inf
  }
  RaphaelPkg/Sec/Sec.inf
  MdeModulePkg/Core/Dxe/DxeMain.inf
  MdeModulePkg/Core/RuntimeDxe/RuntimeDxe.inf {
    <BuildOptions>
      CLANGPDB:*_CLANGPDB_AARCH64_DLINK_FLAGS = /ALIGN:65536 /FILEALIGN:65536
  }
  RaphaelPkg/Drivers/SplashGopDxe/SplashGopDxe.inf
  RaphaelPkg/Drivers/PmicInputDxe/PmicInputDxe.inf
  RaphaelPkg/Drivers/DiagnosticReturnDxe/DiagnosticReturnDxe.inf

[BuildOptions]
  # GenFv XIP rebasing requires equal file/section alignment.
  CLANGPDB:*_CLANGPDB_AARCH64_DLINK_FLAGS = /FILEALIGN:4096
