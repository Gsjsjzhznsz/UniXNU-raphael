# SPDX-License-Identifier: BSD-2-Clause-Patent
# Compile the standalone alias engine; no FD, SEC or allocator integration.
[Defines]
  PLATFORM_NAME = RaphaelRamAlias
  PLATFORM_GUID = CB5188EC-8268-4E20-BE9A-508B5416E8C5
  PLATFORM_VERSION = 0.1
  DSC_SPECIFICATION = 0x0001001C
  OUTPUT_DIRECTORY = Build/RaphaelRamAlias
  SUPPORTED_ARCHITECTURES = AARCH64
  BUILD_TARGETS = DEBUG|RELEASE
  SKUID_IDENTIFIER = DEFAULT

[Components]
  RaphaelPkg/Library/RaphaelRamAliasLib/RaphaelRamAliasLib.inf
