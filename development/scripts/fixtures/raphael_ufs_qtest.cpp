// SPDX-License-Identifier: BSD-2-Clause-Patent
// Drive the same transport against QEMU's real PCI UFS controller model.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <stdexcept>
#include <chrono>
#include <thread>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsTransport.h"
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelReadOnlyExtents.h"
#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelUfsWritePolicy.h"
using namespace RaphaelUfs;
static void check(bool ok,const char *s){if(!ok)throw std::runtime_error(s);printf("PASS %s\n",s);fflush(stdout);}
struct Qtest {
 int fd;uint64_t bar,ram;unsigned writes=0;bool deny=false,badTag=false,stuck=false,badResidual=false,badStatus=false,badOcs=false;unsigned submits=0;uint8_t lastRequest[128]{};uint32_t lastTrd=0;
 Qtest(const char *path,uint64_t b,uint64_t r):bar(b),ram(r){
  fd=socket(AF_UNIX,SOCK_STREAM,0);sockaddr_un a{};a.sun_family=AF_UNIX;check(strlen(path)<sizeof(a.sun_path),"qtest socket path");strcpy(a.sun_path,path);
  int rc=-1;for(unsigned i=0;i<100;++i){rc=connect(fd,reinterpret_cast<sockaddr *>(&a),sizeof(a));if(rc==0)break;std::this_thread::sleep_for(std::chrono::milliseconds(10));}
  check(rc==0,"connect real QEMU qtest");
 }
 ~Qtest(){close(fd);}
 std::string ask(const std::string &s){
  std::string data=s+"\n";size_t at=0;while(at<data.size()){ssize_t n=::write(fd,data.data()+at,data.size()-at);if(n<=0)throw std::runtime_error("qtest write");at+=size_t(n);}
  std::string line;char c;while(line.size()<600000){if(::read(fd,&c,1)!=1)throw std::runtime_error("qtest read");if(c=='\n')break;line+=c;}
  if(line.rfind("OK",0)!=0)throw std::runtime_error("qtest: "+line);
  return line;
 }
 uint32_t physicalRead(uint64_t a){char s[80];snprintf(s,sizeof(s),"readl 0x%llx",(unsigned long long)a);return uint32_t(std::stoull(ask(s).substr(3),nullptr,0));}
 void physicalWrite(uint64_t a,uint32_t v){char s[100];snprintf(s,sizeof(s),"writel 0x%llx 0x%x",(unsigned long long)a,v);ask(s);++writes;}
 uint32_t read(unsigned off){if(stuck&&off==0x58)return 1;return physicalRead(bar+off);}
 void write(unsigned off,uint32_t v){physicalWrite(bar+off,v);if(off==0x58)++submits;}
 bool dmaAllowed(uint64_t a,uint64_t n){return !deny&&a>=ram+0x10000&&a<=ram+0x20000&&n<=ram+0x20000-a;}
 bool toDevice(uint64_t a,const void *p,size_t n){
  if(!dmaAllowed(a,n))return false;
  if(a==ram+0x11000&&n==128)memcpy(lastRequest,p,128);
  if(a==ram+0x10000&&n==32)lastTrd=getle32(static_cast<const uint8_t *>(p));
  char s[100];snprintf(s,sizeof(s),"write 0x%llx %zu 0x",(unsigned long long)a,n);std::string cmd=s;
  const auto *b=static_cast<const uint8_t *>(p);const char *hex="0123456789abcdef";for(size_t i=0;i<n;++i){cmd+=hex[b[i]>>4];cmd+=hex[b[i]&15];}ask(cmd);return true;
 }
 bool fromDevice(uint64_t a,void *p,size_t n){
  if(!dmaAllowed(a,n))return false;
  char s[100];snprintf(s,sizeof(s),"read 0x%llx %zu",(unsigned long long)a,n);std::string answer=ask(s);if(answer.size()!=5+n*2||answer.substr(0,5)!="OK 0x")return false;
  auto *b=static_cast<uint8_t *>(p);for(size_t i=0;i<n;++i){char h[3]={answer[5+i*2],answer[6+i*2],0};b[i]=uint8_t(strtoul(h,nullptr,16));}
  if(badTag&&a==ram+0x11000+32){b[3]^=1;badTag=false;}
  if(badResidual&&a==ram+0x11000+32){b[15]=1;badResidual=false;}
  if(badStatus&&a==ram+0x11000+32){b[7]=2;badStatus=false;}
  if(badOcs&&a==ram+0x10000){b[8]=1;badOcs=false;}
  return true;
 }
 uint64_t nowUs(){return uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now().time_since_epoch()).count());}
 void pause(){std::this_thread::sleep_for(std::chrono::microseconds(50));}
};
int main(int argc,char **argv){try{
 check(argc==5||argc==6,"explicit model resource inputs");bool writeTest=argc==6&&std::string(argv[5])=="--diagnostic-writes";bool persisted=argc==6&&std::string(argv[5])=="--verify-persisted-write";uint64_t ecam=strtoull(argv[2],nullptr,0),bar=strtoull(argv[3],nullptr,0),ram=strtoull(argv[4],nullptr,0);Qtest io(argv[1],bar,ram);
 // PCI root resources are derived by the runner from this same QEMU's FDT.
 uint64_t cfg=0;for(unsigned slot=0;slot<32;++slot){uint64_t a=ecam+(uint64_t(slot)<<15);uint32_t id=io.physicalRead(a);if(id!=0xffffffffU)printf("PCI slot=%u id=%08x class=%08x\n",slot,id,io.physicalRead(a+8));if((io.physicalRead(a+8)>>16)==0x0109){check(!cfg,"unique QEMU UFS PCI device");cfg=a;}}
 check(cfg!=0,"find QEMU UFS PCI controller");io.physicalWrite(cfg+0x10,uint32_t(bar)|4);io.physicalWrite(cfg+0x14,uint32_t(bar>>32));io.physicalWrite(cfg+4,6);
 check(io.read(8)>=0x200,"UFS HCI version");io.write(0x34,1);
 io.write(0x94,0);io.write(0x98,0);io.write(0x9c,0);io.write(0x90,0x16);
 check((io.read(0x30)&9)==9,"model link startup and device present");
 Dma buffers{ram+0x10000,ram+0x11000,ram+0x12000,16384};Transport<Qtest> t(io,buffers);unsigned before=io.writes;
 check(t.takeOver(false)==Result::NotReady&&io.writes==before,"refuse absent exclusive ownership without register writes");
 io.deny=true;check(t.takeOver(true)==Result::DmaDenied&&io.writes==before,"refuse unowned DMA without register writes");io.deny=false;
 check(t.takeOver(true)==Result::Ok,"install owned polling request list");uint8_t inquiry[36]{};Result v=t.inquiry(0,inquiry);
 if(v!=Result::Ok)printf("inquiry result=%d ocs=%u response=%u status=%u sense=%u/%u/%u\n",int(v),t.last.ocs,t.last.response,t.last.status,t.last.senseKey,t.last.asc,t.last.ascq);
 check(v==Result::Ok,"real UFS INQUIRY command and response");
 // A real freshly-created SCSI LU can report unit attention once. It is
 // explicitly observed and retried here, never hidden by the transport.
 v=t.testUnitReady(0);if(v==Result::ScsiError&&t.last.senseKey==6){printf("OBSERVED unit attention %u/%u\n",t.last.asc,t.last.ascq);v=t.testUnitReady(0);}check(v==Result::Ok,"real UFS TEST UNIT READY");
 Geometry g{};v=t.capacity(0,g);if(v!=Result::Ok)printf("capacity result=%d status=%u sense=%u/%u\n",int(v),t.last.status,t.last.senseKey,t.last.asc);
 check(v==Result::Ok&&g.blocks*g.bytes==40*1024*1024&&g.bytes==4096,"real UFS READ CAPACITY 16 geometry");
 uint8_t block[4096]{};check(t.read(0,7,1,block,sizeof(block))==Result::Ok,"real UFS READ 16 DMA completion");bool same=true;for(unsigned i=0;i<sizeof(block);++i)same=same&&block[i]==uint8_t((i*29+7)&255);check(same,"all known block bytes match synthetic disk");
 check(t.read(0,g.blocks,1,block,sizeof(block))==Result::Invalid,"reject capacity boundary");check(t.read(0,0,2,block,sizeof(block))==Result::Invalid,"reject caller byte mismatch");
 io.badTag=true;check(t.read(0,7,1,block,sizeof(block))==Result::ResponseError,"reject mismatched response task tag");
 v=t.inquiry(31,inquiry);printf("absent lun result=%d ocs=%u response=%u status=%u sense=%u/%u/%u\n",int(v),t.last.ocs,t.last.response,t.last.status,t.last.senseKey,t.last.asc,t.last.ascq);check(v==Result::ControllerError&&t.last.ocs==1,"report real nonexistent LUN rejected by controller OCS");
 check(t.restore()==Result::Ok&&!t.dmaMustRemainReserved(),"restore inherited register configuration");
 Transport<Qtest> read10(io,buffers,ReadCommand::Read10);check(read10.takeOver(true)==Result::Ok,"explicit READ10 mode attaches");
 Geometry g10{};check(read10.capacity(0,g10)==Result::Ok,"READ10 mode obtains real capacity");
 memset(block,0,sizeof(block));check(read10.read(0,7,1,block,sizeof(block))==Result::Ok,"real UFS READ10 DMA completion");same=true;for(unsigned i=0;i<sizeof(block);++i)same=same&&block[i]==uint8_t((i*29+7)&255);check(same,"READ10 exact full block matches READ16 source");
 uint8_t bulk[16384]{};unsigned submitted=io.submits;
 check(read10.read(0,6,4,bulk,sizeof(bulk))==Result::Ok&&io.submits==submitted+1,"four physical blocks complete in one real READ10 command");
 same=true;for(unsigned i=0;i<sizeof(bulk);++i)same=same&&bulk[i]==(i>=4096&&i<8192?uint8_t((i-4096)*29+7):0);check(same,"all16KiB model bytes match including known middle block");
 check(getbe32(io.lastRequest+12)==16384&&io.lastRequest[23]==0&&io.lastRequest[24]==4,"READ10 encodes16KiB transfer with four-block count");
 memset(bulk,0xa5,sizeof(bulk));io.badResidual=true;submitted=io.submits;
 check(read10.read(0,6,4,bulk,sizeof(bulk))==Result::Residual&&io.submits==submitted+1,"multi-block residual fails without retry");
 same=true;for(auto byte:bulk)same=same&&byte==0xa5;check(same,"failed multi-block response publishes no payload");
 RaphaelStorage::ReadOnlyExtents file;
 RaphaelStorage::Bounds bounds{8192,g10.blocks*g10.bytes,4096,g10.blocks*g10.bytes-4096,4096,512};
 RaphaelStorage::Extent extents[]={{0,7*4096,4096,0},{4096,9*4096,4096,1}};
 check(file.initialize(extents,2,bounds)==RaphaelStorage::Result::Ok,"read-only fragmented file mapper validates real model geometry");
 struct Blocks {Transport<Qtest> &t;bool readPhysicalBlocks(uint64_t lba,uint32_t n,uint8_t *out){return t.read(0,lba,n,out,n*4096)==Result::Ok;}bool readPhysicalBlock(uint64_t lba,uint8_t *out){return t.read(0,lba,1,out,4096)==Result::Ok;}} blocks{read10};
 memset(block,0xa5,sizeof(block));
 check(file.read(blocks,3584,1024,block)==RaphaelStorage::Result::Ok,"512-byte virtual sectors cross fragmented extents through real READ10");
 same=true;for(unsigned i=0;i<1024;++i)same=same&&block[i]==(i<512?uint8_t((3584+i)*29+7):0);
 check(same,"cross-extent bounce data exactly matches real disk");
 check(file.read(blocks,8192,512,block)==RaphaelStorage::Result::InvalidRead,"mapped virtual EOF refuses access to unrelated disk blocks");
 memset(bulk,0xa5,sizeof(bulk));submitted=io.submits;
 check(file.readAligned(blocks,0,8192,bulk)==RaphaelStorage::Result::Ok&&io.submits==submitted+2,"batched mapper splits real READ10 at fragmented extent boundary");
 same=true;for(unsigned i=0;i<8192;++i)same=same&&bulk[i]==(i<4096?uint8_t(i*29+7):0);check(same,"batched fragmented mapping matches exact model data");
 if(persisted){
  check(read10.read(0,11,1,block,sizeof(block))==Result::Ok,"restarted controller reads persisted diagnostic block");
  same=true;for(unsigned i=0;i<sizeof(block);++i)same=same&&block[i]==uint8_t(i*13+0x63);
  check(same,"persisted block exact after full QEMU process restart");
 }
 if(writeTest){
  uint8_t pattern[4096];for(unsigned i=0;i<sizeof(pattern);++i)pattern[i]=uint8_t(i*13+0x63);
  before=io.writes;
  check(read10.writeDiagnostic(0,11,1,pattern,sizeof(pattern))==Result::WriteDenied&&io.writes==before,"default transport refuses media writes without register IO");
  check(read10.flushDiagnostic()==Result::WriteDenied&&io.writes==before,"default transport refuses flush without write window");
  DiagnosticWriteWindow window{11,1,g10.blocks,4096,0},bad=window;bad.lunBlocks++;
  check(read10.enableDiagnosticWrites(bad)==Result::WriteDenied,"write window requires actual capacity match");
  bad=window;bad.lun=1;check(read10.enableDiagnosticWrites(bad)==Result::WriteDenied,"diagnostic writes reject other LUN");
  bad=window;bad.first=0;check(read10.enableDiagnosticWrites(bad)==Result::WriteDenied,"diagnostic writes reject GPT LBA0");
  bad=window;bad.blocks=8193;check(read10.enableDiagnosticWrites(bad)==Result::WriteDenied,"diagnostic allocation bounded to32MiB");
  bad=window;bad.first=g10.blocks;check(read10.enableDiagnosticWrites(bad)==Result::WriteDenied,"write window refuses capacity overflow");
  RaphaelStorage::UfsWritePolicy policy{0x3157525346485052ULL,1,g10.blocks,1,g10.blocks-1,11,1,4096,{},{}};
  memcpy(policy.replacement,pattern,4096);
  check(RaphaelStorage::validateWritePolicy(policy,11),"firmware write policy validates exact allocation");
  uint64_t flags=0;policy.original[0]=1;before=io.submits;
  check(RaphaelStorage::executeWriteProbe(policy,read10,block,flags)==201&&flags==1&&io.submits==before+1,"firmware preimage mismatch prevents any media write");policy.original[0]=0;
  check(RaphaelStorage::executeWriteProbe(policy,read10,block,flags)==0&&flags==63,"actual firmware probe preimage/FUA/flush/readback succeeds");
  check(read10.enableDiagnosticWrites(window)==Result::WriteDenied,"write allocation cannot be widened after activation");
  before=io.writes;
  check(read10.writeDiagnostic(0,10,1,pattern,sizeof(pattern))==Result::WriteDenied&&io.writes==before,"reject write immediately below allocation");
  check(read10.writeDiagnostic(0,12,1,pattern,sizeof(pattern))==Result::WriteDenied&&io.writes==before,"reject write immediately above allocation");
  check(read10.writeDiagnostic(0,11,2,pattern,sizeof(pattern))==Result::WriteDenied&&io.writes==before,"reject crossing write allocation end");
  check(read10.writeDiagnostic(1,11,1,pattern,sizeof(pattern))==Result::WriteDenied&&io.writes==before,"reject wrong write LUN without submission");
  check(read10.writeDiagnostic(0,11,1,pattern,512)==Result::Invalid&&io.writes==before,"reject partial native block write");
  check(read10.writeDiagnostic(0,11,1,nullptr,4096)==Result::Invalid&&io.writes==before,"reject missing write payload");
  check(read10.writeDiagnostic(0,11,1,pattern,sizeof(pattern))==Result::Ok,"real WRITE10 completes on QEMU UFS");
  check(io.lastRequest[1]==0x21&&io.lastRequest[16]==0x2a&&io.lastRequest[17]==8&&((io.lastTrd>>25)&3)==1,"WRITE10 FUA and data-out direction encoded");
  check(read10.flushDiagnostic()==Result::Ok,"synchronous SYNCHRONIZE CACHE10 completes");
  check(io.lastRequest[16]==0x35&&io.lastRequest[17]==0&&getbe32(io.lastRequest+18)==11&&io.lastRequest[24]==1&&((io.lastTrd>>25)&3)==0,"flush exact allocation with IMMED0 and no data phase");
  check(read10.read(0,11,1,block,sizeof(block))==Result::Ok&&memcmp(block,pattern,sizeof(block))==0,"READ10 exact readback of written block");
  unsigned sent=io.submits;io.badResidual=true;
  check(read10.writeDiagnostic(0,11,1,pattern,sizeof(pattern))==Result::Residual&&io.submits==sent+1,"write residual rejected without implicit retry");
  sent=io.submits;io.badStatus=true;
  check(read10.flushDiagnostic()==Result::ScsiError&&io.submits==sent+1,"flush SCSI failure is not durability success");
  sent=io.submits;io.badOcs=true;
  check(read10.writeDiagnostic(0,11,1,pattern,sizeof(pattern))==Result::ControllerError&&io.submits==sent+1,"write OCS failure preserved without retry");
  check(read10.flushDiagnostic()==Result::Ok,"final successful bounded flush after explicit fault tests");
  for(uint64_t lba:{10ULL,12ULL}){check(read10.read(0,lba,1,block,sizeof(block))==Result::Ok,"read allocation guard block");same=true;for(auto c:block)same=same&&c==0;check(same,"adjacent unallocated guard block untouched");}
 }
 if(writeTest){
  read10.revokeDiagnosticWrites();before=io.writes;
  check(read10.writeDiagnostic(0,11,1,block,sizeof(block))==Result::WriteDenied&&io.writes==before,"explicit diagnostic revocation refuses writes without IO");
  check(read10.flushDiagnostic()==Result::WriteDenied&&io.writes==before,"explicit diagnostic revocation refuses flush without IO");
  check(read10.enableDiagnosticWrites({11,1,g10.blocks,4096,0})==Result::WriteDenied&&io.writes==before,"revocation cannot reopen or enlarge a spent write grant");
  check(read10.read(0,11,1,block,sizeof(block))==Result::Ok,"read session remains usable after diagnostic revocation");
 }
 check(read10.restore()==Result::Ok,"READ10 mode restores inherited configuration");
 before=io.writes;check(read10.writeDiagnostic(0,11,1,block,sizeof(block))==Result::WriteDenied&&io.writes==before,"restoration revokes write authorization");
 if(writeTest){
  Transport<Qtest> wide(io,buffers,ReadCommand::Read10);check(wide.takeOver(true)==Result::Ok,"32MiB log transport attaches");Geometry gw{};check(wide.capacity(0,gw)==Result::Ok,"32MiB log obtains actual model capacity");
  check(wide.enableDiagnosticWrites({64,8192,gw.blocks,4096,0})==Result::Ok,"accept exact32MiB log window");
  uint8_t pat[4096];for(unsigned i=0;i<sizeof(pat);++i)pat[i]=uint8_t(i*13+0x63);
  for(uint64_t lba:{64ULL,8255ULL}){check(wide.writeDiagnostic(0,lba,1,pat,sizeof(pat))==Result::Ok,"32MiB window first/last WRITE10");check(wide.flushDiagnostic()==Result::Ok,"32MiB log flush");check(wide.read(0,lba,1,block,sizeof(block))==Result::Ok&&!memcmp(block,pat,sizeof(block)),"32MiB window exact readback");}
  before=io.writes;check(wide.writeDiagnostic(0,8256,1,pat,sizeof(pat))==Result::WriteDenied&&io.writes==before,"32MiB upper guard rejected without IO");
  check(wide.restore()==Result::Ok,"32MiB log restores inherited controller");
 }
 Transport<Qtest> timeout(io,buffers);check(timeout.takeOver(true)==Result::Ok,"independent timeout case owns buffers");
 io.stuck=true;check(timeout.testUnitReady(0)==Result::Busy,"refuse outstanding request before submission");io.stuck=false;
 // Force an actual submitted request to appear incomplete to the caller.
 struct TimedIo {Qtest &q;bool sent=false;uint32_t read(unsigned o){return sent&&o==0x58?1:q.read(o);}void write(unsigned o,uint32_t v){q.write(o,v);if(o==0x58)sent=true;}
  bool dmaAllowed(uint64_t a,uint64_t n){return q.dmaAllowed(a,n);}bool toDevice(uint64_t a,const void *p,size_t n){return q.toDevice(a,p,n);}bool fromDevice(uint64_t a,void *p,size_t n){return q.fromDevice(a,p,n);}uint64_t nowUs(){return q.nowUs();}void pause(){q.pause();}} delayed{io};
 check(timeout.restore()==Result::Ok,"close preliminary busy case");Transport<TimedIo> stalled(delayed,buffers);check(stalled.takeOver(true)==Result::Ok,"timeout adapter attaches");
 check(stalled.testUnitReady(0)==Result::Timeout&&stalled.dmaMustRemainReserved(),"timeout quarantines DMA buffers");check(stalled.restore()==Result::Poisoned,"refuse unsafe DMA release after timeout");
 check(stalled.resetAfterError()==Result::Ok&&!stalled.dmaMustRemainReserved()&&io.read(0x34)==0,"explicit HCE reset quiesces poisoned model DMA before release");
 check(stalled.read(0,0,1,block,sizeof(block))==Result::Invalid,"reset transport cannot issue IO before fresh controller initialization");
 puts("RAPHAEL_UFS_QTEST_OK");return 0;
 }catch(const std::exception &e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
