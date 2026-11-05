// SPDX-License-Identifier: BSD-2-Clause-Patent
// Executes unchanged upstream RAM-disk implementation with a synthetic local HOB.
// All allocations and devices here belong to AAVMF/QEMU, never a handset.
#include <PiDxe.h>
#include <Library/TimerLib.h>
#include <Library/UefiBootServicesTableLib.h>
#ifdef RAPHAEL_MANAGER_UI_FIXTURE
#include <Library/RaphaelManagerUiLib.h>
#include <Library/RaphaelManagerInputLib.h>
#include <Protocol/SimpleTextIn.h>
#include <Protocol/DevicePath.h>
STATIC BOOLEAN mUiKeys,mUiPending,mUiFallback;
STATIC UINTN mUiNext;
STATIC UINT64 mUiStart;
STATIC EFI_INPUT_KEY mUiKey;
STATIC UINT64 ManagerInputCounter(VOID){return GetPerformanceCounter();}
STATIC EFI_STATUS EFIAPI UiReset(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,BOOLEAN Verify){(VOID)This;(VOID)Verify;mUiPending=FALSE;return EFI_SUCCESS;}
STATIC EFI_STATUS EFIAPI UiRead(EFI_SIMPLE_TEXT_INPUT_PROTOCOL *This,EFI_INPUT_KEY *Key){(VOID)This;if(!Key)return EFI_INVALID_PARAMETER;if(!mUiPending)return EFI_NOT_READY;*Key=mUiKey;mUiPending=FALSE;++mUiNext;return EFI_SUCCESS;}
STATIC VOID EFIAPI UiWait(EFI_EVENT Event,VOID *Context){
 (VOID)Context;
 if(mUiKeys&&!mUiPending&&mUiNext<(mUiFallback?1:3)&&GetTimeInNanoSecond(GetPerformanceCounter()-mUiStart)>=(mUiNext+1)*350000000ULL){
  mUiKey.ScanCode=mUiNext==0?SCAN_UP:mUiNext==1?SCAN_DOWN:SCAN_NULL;
  mUiKey.UnicodeChar=mUiNext==2?CHAR_CARRIAGE_RETURN:0;mUiPending=TRUE;
 }
 if(mUiPending)gBS->SignalEvent(Event);
}
STATIC struct {VENDOR_DEVICE_PATH Vendor;EFI_DEVICE_PATH_PROTOCOL End;} mUiPath={
 {{HARDWARE_DEVICE_PATH,HW_VENDOR_DP,{sizeof(VENDOR_DEVICE_PATH),0}},{0xbfe23c94,0x158d,0x48b1,{0xa9,0x44,0x7b,0x8f,0xf3,0x14,0x52,0x17}}},
 {END_DEVICE_PATH_TYPE,END_ENTIRE_DEVICE_PATH_SUBTYPE,{sizeof(EFI_DEVICE_PATH_PROTOCOL),0}}};
#endif
#include <PayloadFixture.h>
#include <Library/UefiRuntimeServicesTableLib.h>
#include <Library/TimerLib.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/SimpleFileSystem.h>
#include <../Library/UniXNULib/Internal.h>
#include <../Driver/UniXNURamDiskDxe/UniXNURamDiskDxe.c>
extern VOID *mHobList;
STATIC UINTN mPass,mFail;
STATIC VOID Check(CONST CHAR8 *Name,BOOLEAN Ok) {
  UniXNULog("PAYLOAD_FIXTURE_%a %a",Ok?"PASS":"FAIL",Name);if(Ok)++mPass;else ++mFail;
}
EFI_STATUS EFIAPI PayloadFixtureEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *Table) {
  EFI_STATUS S;EFI_LOADED_IMAGE_PROTOCOL *Loaded;VOID *Data=NULL;UINTN Bytes=0;
  VOID *Dtb=AllocateZeroPool(4096);EFI_HANDLE *Handles=NULL,Ram=NULL;UINTN Count=0;
  struct {EFI_HOB_GUID_TYPE Guid;UINT64 Dtb;EFI_HOB_GENERIC_HEADER End;} H;
  VOID *SavedHob=mHobList;UINT8 Block[512],Original[512];EFI_BLOCK_IO_PROTOCOL *Io;
  EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *Fs=NULL;EFI_FILE_PROTOCOL *Root=NULL,*File=NULL;
  UNIXNU_CONFIG Config;EFI_GUID Guid=FIXTURE_GUID;EFI_HANDLE TestHandle=NULL;
  FIXTURE_RESULT R={FIXTURE_MAGIC,0,0,0,Image};
  UniXNULogInit();UniXNULog("PAYLOAD_FIXTURE_START synthetic HOB and RAM FAT; AAVMF supplies DiskIo/FAT/timer");
  S=gBS->HandleProtocol(Image,&gEfiLoadedImageProtocolGuid,(VOID **)&Loaded);
  if(EFI_ERROR(S)||!Dtb)goto Failed;
  S=UniXNUReadFile(Loaded->DeviceHandle,L"\\payload.img",&Data,&Bytes);
  Check("FAT image read",!EFI_ERROR(S)&&Bytes==1048576);if(EFI_ERROR(S)||Bytes!=1048576)goto Failed;
  if(FdtCreateEmptyTree(Dtb,4096))goto Failed;
  INT32 Chosen=FdtAddSubnode(Dtb,0,"chosen");if(Chosen<0)goto Failed;
  if(FdtSetPropU64(Dtb,Chosen,"linux,initrd-start",(UINTN)Data)||FdtSetPropU64(Dtb,Chosen,"linux,initrd-end",(UINTN)Data+Bytes))goto Failed;
  ZeroMem(&H,sizeof(H));H.Guid.Header.HobType=EFI_HOB_TYPE_GUID_EXTENSION;H.Guid.Header.HobLength=sizeof(H.Guid)+8;
  CopyGuid(&H.Guid.Name,&mEntryArgHobGuid);H.Dtb=(UINTN)Dtb;H.End.HobType=EFI_HOB_TYPE_END_OF_HOB_LIST;H.End.HobLength=sizeof(H.End);
  mHobList=&H;S=UniXNURamDiskDxeEntry(Image,Table);mHobList=SavedHob;
  Check("actual RAM-disk entry",!EFI_ERROR(S));if(EFI_ERROR(S))goto Failed;
  S=gBS->LocateHandleBuffer(ByProtocol,&gEfiBlockIoProtocolGuid,NULL,&Count,&Handles);if(EFI_ERROR(S))goto Failed;
  for(UINTN I=0;I<Count;++I)if(!EFI_ERROR(gBS->HandleProtocol(Handles[I],&gEfiBlockIoProtocolGuid,(VOID **)&Io))&&Io==&mBlockIo)Ram=Handles[I];
  FreePool(Handles);Check("read-only BlockIo published",Ram&&mMedia.ReadOnly&&mMedia.BlockSize==512&&mMedia.LastBlock==2047);if(!Ram)goto Failed;
  S=mBlockIo.ReadBlocks(&mBlockIo,mMedia.MediaId,0,512,Block);CopyMem(Original,Block,512);
  Check("first sector identity",!EFI_ERROR(S)&&CompareMem(Block,Data,512)==0);
  Check("media mismatch refused",mBlockIo.ReadBlocks(&mBlockIo,mMedia.MediaId+1,0,512,Block)==EFI_MEDIA_CHANGED);
  Check("partial sector refused",mBlockIo.ReadBlocks(&mBlockIo,mMedia.MediaId,0,511,Block)==EFI_BAD_BUFFER_SIZE);
  Check("LBA beyond end refused",mBlockIo.ReadBlocks(&mBlockIo,mMedia.MediaId,2048,512,Block)==EFI_INVALID_PARAMETER);
  SetMem(Block,512,0x5a);S=mBlockIo.WriteBlocks(&mBlockIo,mMedia.MediaId,0,512,Block);
  Check("block writes refused",S==EFI_WRITE_PROTECTED&&CompareMem(Original,Data,512)==0);
  S=gBS->ConnectController(Ram,NULL,NULL,TRUE);Check("RAM FAT controller connected",!EFI_ERROR(S));
  S=gBS->HandleProtocol(Ram,&gEfiSimpleFileSystemProtocolGuid,(VOID **)&Fs);
  Check("RAM FAT filesystem",!EFI_ERROR(S)&&Fs);if(EFI_ERROR(S)||!Fs)goto Failed;
  S=Fs->OpenVolume(Fs,&Root);if(EFI_ERROR(S))goto Failed;
  S=Root->Open(Root,&File,L"\\EFI\\UniXNU\\unixnu.toml",EFI_FILE_MODE_READ|EFI_FILE_MODE_WRITE,0);
  Check("file write open refused",S==EFI_WRITE_PROTECTED||S==EFI_ACCESS_DENIED);if(!EFI_ERROR(S))File->Close(File);
  Root->Close(Root);
#ifdef RAPHAEL_MANAGER_UI_FIXTURE
  UINTN ExpectedEntries=3,ProbeIndex=2;
#else
  UINTN ExpectedEntries=2,ProbeIndex=0;
#endif
  UniXNUConfigLoad(Image,&Config);
  Check("config read from RAM",Config.Volume==Ram&&Config.EntryCount==ExpectedEntries&&Config.Error[0]==0);
  Check("config default exit",Config.EntryCount==ExpectedEntries&&Config.DefaultIndex==1&&Config.Timeout==2&&Config.Entries[1].Type==UniXNUEntryAction&&Config.Entries[1].Action==UniXNUActionExit);
  if(Config.EntryCount!=ExpectedEntries||Config.Volume!=Ram)goto Failed;
  S=gBS->InstallMultipleProtocolInterfaces(&TestHandle,&Guid,&R,NULL);if(EFI_ERROR(S))goto Failed;
  S=UniXNUBootEntry(Image,&Config,&Config.Entries[ProbeIndex]);
  Check("EFI payload returned",!EFI_ERROR(S));Check("EFI child handshake",R.Calls==1&&R.OptionsOk&&R.ParentOk);
  gBS->UninstallMultipleProtocolInterfaces(TestHandle,&Guid,&R,NULL);
#ifdef RAPHAEL_MANAGER_UI_FIXTURE
  EFI_GRAPHICS_OUTPUT_PROTOCOL *Gop=NULL;
  S=gBS->LocateProtocol(&gEfiGraphicsOutputProtocolGuid,NULL,(VOID **)&Gop);if(EFI_ERROR(S)||!Gop||!Gop->Mode||!Gop->Mode->Info)goto Failed;
  UniXNULog("MANAGER_UI_GOP width=%u height=%u pitch=%u format=%u base=%lx bytes=%lu",Gop->Mode->Info->HorizontalResolution,Gop->Mode->Info->VerticalResolution,Gop->Mode->Info->PixelsPerScanLine,(UINT32)Gop->Mode->Info->PixelFormat,Gop->Mode->FrameBufferBase,Gop->Mode->FrameBufferSize);
  RAPHAEL_GOP_RESULT Expected={0};Expected.Base=Gop->Mode->FrameBufferBase;Expected.Extent=Gop->Mode->FrameBufferSize;
  Expected.Width=Gop->Mode->Info->HorizontalResolution;Expected.Height=Gop->Mode->Info->VerticalResolution;Expected.Stride=Gop->Mode->Info->PixelsPerScanLine*4;
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL Input={UiReset,UiRead,NULL};EFI_HANDLE InputHandle=NULL;
  S=gBS->CreateEvent(EVT_NOTIFY_WAIT,TPL_CALLBACK,UiWait,NULL,&Input.WaitForKey);if(EFI_ERROR(S))goto Failed;
  S=gBS->InstallMultipleProtocolInterfaces(&InputHandle,&gEfiSimpleTextInProtocolGuid,&Input,&gEfiDevicePathProtocolGuid,&mUiPath,NULL);if(EFI_ERROR(S))goto Failed;
  EFI_SIMPLE_TEXT_INPUT_PROTOCOL *SavedInput=gST->ConIn;EFI_HANDLE SavedInputHandle=gST->ConsoleInHandle;UINT32 SavedCrc=gST->Hdr.CRC32;
  gST->ConIn=&Input;gST->ConsoleInHandle=InputHandle;gST->Hdr.CRC32=0;gBS->CalculateCrc32(gST,gST->Hdr.HeaderSize,&gST->Hdr.CRC32);
  UINT64 Ns=0;
  for(UINTN Round=0;Round<3;++Round){
    RAPHAEL_MANAGER_UI_STATE Ui={0};mUiKeys=Round!=0;mUiFallback=Round==2;mUiPending=FALSE;mUiNext=0;
    S=RaphaelManagerUiBegin(&Ui,&Expected,TRUE,Gop);Check("actual manager framebuffer backed up",!EFI_ERROR(S)&&Ui.Result.Status==2);if(EFI_ERROR(S))goto Failed;
    UniXNULog("PAYLOAD_FIXTURE_MENU normal UniXNURun; actual framebuffer transaction; synthetic_keys=%u",(UINT32)mUiKeys);
    RAPHAEL_MANAGER_INPUT Bounded={0};EFI_HANDLE WrapperHandle=NULL;
    S=RaphaelManagerInputBegin(&Bounded,&Input,ManagerInputCounter,GetPerformanceCounterProperties(NULL,NULL),6);
    Check("bounded input wrapper event",!EFI_ERROR(S));if(EFI_ERROR(S))goto Failed;
    S=gBS->InstallProtocolInterface(&WrapperHandle,&gEfiSimpleTextInProtocolGuid,EFI_NATIVE_INTERFACE,&Bounded.Protocol);if(EFI_ERROR(S))goto Failed;
    UINT32 RoundCrc=gST->Hdr.CRC32;gST->ConIn=&Bounded.Protocol;gST->ConsoleInHandle=WrapperHandle;gST->Hdr.CRC32=0;gBS->CalculateCrc32(gST,gST->Hdr.HeaderSize,&gST->Hdr.CRC32);
    mUiStart=GetPerformanceCounter();S=UniXNURun(Image,UniXNUHostApplication);Ns=GetTimeInNanoSecond(GetPerformanceCounter()-mUiStart);
    gST->ConIn=&Input;gST->ConsoleInHandle=InputHandle;gST->Hdr.CRC32=RoundCrc;
    EFI_STATUS Uninstalled=gBS->UninstallProtocolInterface(WrapperHandle,&gEfiSimpleTextInProtocolGuid,&Bounded.Protocol);
    EFI_STATUS Closed=RaphaelManagerInputEnd(&Bounded);
    Check("bounded console protocol restored and event closed",!EFI_ERROR(Uninstalled)&&!EFI_ERROR(Closed));
    if(Round==0)Check("timeout without invented physical keys",!Bounded.Up&&!Bounded.Down&&!Bounded.Enter&&!Bounded.Automatic&&!Bounded.Errors);
    if(Round==1)Check("wrapper delivered physical-shaped Up Down Enter",Bounded.Up==1&&Bounded.Down==1&&Bounded.Enter==1&&!Bounded.Automatic&&!Bounded.Errors);
    if(Round==2)Check("deadline after first key cannot claim physical Enter",Bounded.Up==1&&!Bounded.Down&&!Bounded.Enter&&Bounded.Automatic==1&&!Bounded.Errors);
    Check("UniXNURun exits",!EFI_ERROR(S));
    if(Round==0)Check("periodic timeout elapsed",Ns>=1800000000ULL&&Ns<15000000000ULL);
    else if(Round==1)Check("full manager consumed Up Down Enter before timeout",mUiNext==3&&!mUiPending&&Ns>=1050000000ULL&&Ns<2000000000ULL);
    if(Round==2)Check("absolute input deadline after upstream countdown cancelled",mUiNext==1&&Ns>=5800000000ULL&&Ns<8000000000ULL);
    S=RaphaelManagerUiFinish(&Ui);Check("actual manager changed and restored full framebuffer",!EFI_ERROR(S)&&Ui.Result.Status==4&&Ui.Result.PixelsChanged>0&&Ui.Result.PixelsRestored==Expected.Width*Expected.Height&&!Ui.Result.Mismatches&&!Ui.Result.Active&&!Ui.Result.Backup);
    UniXNULog("MANAGER_INPUT_FIXTURE_RESULT round=%u up=%lu down=%lu enter=%lu automatic=%lu errors=%lu",(UINT32)Round,Bounded.Up,Bounded.Down,Bounded.Enter,Bounded.Automatic,Bounded.Errors);
    UniXNULog("MANAGER_UI_FIXTURE_RESULT round=%u width=%lu height=%lu changed=%lu restored=%lu mismatch=%lu keys=%u elapsed_ns=%lu",(UINT32)Round,Expected.Width,Expected.Height,Ui.Result.PixelsChanged,Ui.Result.PixelsRestored,Ui.Result.Mismatches,(UINT32)mUiNext,Ns);
  }
  gST->ConIn=SavedInput;gST->ConsoleInHandle=SavedInputHandle;gST->Hdr.CRC32=SavedCrc;
  gBS->UninstallMultipleProtocolInterfaces(InputHandle,&gEfiSimpleTextInProtocolGuid,&Input,&gEfiDevicePathProtocolGuid,&mUiPath,NULL);gBS->CloseEvent(Input.WaitForKey);
#else
  UniXNULog("PAYLOAD_FIXTURE_MENU normal UniXNURun; AAVMF timers");
  UINT64 Start=GetPerformanceCounter();S=UniXNURun(Image,UniXNUHostApplication);UINT64 Ns=GetTimeInNanoSecond(GetPerformanceCounter()-Start);
  Check("UniXNURun exits",!EFI_ERROR(S));Check("periodic timeout elapsed",Ns>=1800000000ULL&&Ns<15000000000ULL);
#endif
  UniXNULog("PAYLOAD_FIXTURE_RESULT passed=%u failed=%u elapsed_ns=%lu",(UINT32)mPass,(UINT32)mFail,Ns);
  UniXNULog("PAYLOAD_FIXTURE_%a",mFail?"FAILED":"OK");
  gRT->ResetSystem(EfiResetShutdown,mFail?EFI_ABORTED:EFI_SUCCESS,0,NULL);return mFail?EFI_ABORTED:EFI_SUCCESS;
Failed:
  mHobList=SavedHob;UniXNULog("PAYLOAD_FIXTURE_FAILED early status=%r",S);gRT->ResetSystem(EfiResetShutdown,EFI_ABORTED,0,NULL);return EFI_ABORTED;
}
