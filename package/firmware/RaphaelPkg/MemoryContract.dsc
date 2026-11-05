# SPDX-License-Identifier: BSD-2-Clause-Patent
# Compile the platform memory validator without selecting an active FD layout.
[Defines]
  PLATFORM_NAME = RaphaelMemoryContract
  PLATFORM_GUID = 3B310780-BF07-4BCF-9822-7B04BA603EB1
  PLATFORM_VERSION = 0.1
  DSC_SPECIFICATION = 0x0001001C
  OUTPUT_DIRECTORY = Build/RaphaelMemoryContract
  SUPPORTED_ARCHITECTURES = AARCH64
  BUILD_TARGETS = DEBUG|RELEASE
  SKUID_IDENTIFIER = DEFAULT

[Components]
  RaphaelPkg/Library/RaphaelMemoryContractLib/RaphaelMemoryContractLib.inf
