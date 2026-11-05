#include "../../UniXNU-sm8150-common/kits/Sm8150Platform/RaphaelPayloadHash.h"
#include <cstdio>
#include <cstring>
#include <vector>
using namespace RaphaelStorage;
struct Device {
 std::vector<uint8_t> data;bool corrupt=false,fail=false;
 bool readPhysicalBlock(uint64_t n,uint8_t *out){if(n<1||n>2||fail)return false;memcpy(out,data.data()+(n-1)*4096,4096);if(corrupt&&n==2)out[17]^=1;return true;}
};
int main(){
 uint8_t block[4096],digest[32];
 while(fread(block,1,4096,stdin)==4096){payloadHash(block,digest);for(auto v:digest)printf("%02x",v);puts("");}
 Device device;device.data.resize(8192);for(unsigned i=0;i<8192;++i)device.data[i]=static_cast<uint8_t>(i*37+i/11);
 uint8_t hashes[64];payloadHash(device.data.data(),hashes);payloadHash(device.data.data()+4096,hashes+32);
 Extent map{0,4096,8192,1};ReadOnlyExtents disk;Bounds bounds{8192,16384,4096,8192,4096,512};
 auto check=[](bool okay,const char *name){if(!okay){fprintf(stderr,"FAIL %s\n",name);return false;}printf("PASS %s\n",name);return true;};
 if(!check(disk.initialize(&map,1,bounds)==Result::Ok,"map"))return 1;
 uint8_t output[8192],scratch[4096];uint64_t completed=0;
 if(!check(loadPayload(disk,device,hashes,2,output,8192,scratch,completed)&&completed==2&&!memcmp(output,device.data.data(),8192),"entire payload"))return 1;
 memset(output,0xcc,8192);device.corrupt=true;
 if(!check(!loadPayload(disk,device,hashes,2,output,8192,scratch,completed)&&completed==1&&output[4096]==0xcc,"bad block never copied"))return 1;
 device.corrupt=false;device.fail=true;memset(output,0xcc,8192);
 if(!check(!loadPayload(disk,device,hashes,2,output,8192,scratch,completed)&&completed==0&&output[0]==0xcc,"failed read never copied"))return 1;
 if(!check(!loadPayload(disk,device,hashes,2,output,4096,scratch,completed),"capacity mismatch"))return 1;
 if(!check(!loadPayload(disk,device,hashes,0,output,8192,scratch,completed),"zero count"))return 1;
 if(!check(!loadPayload(disk,device,nullptr,2,output,8192,scratch,completed),"no hash table"))return 1;
 device.fail=false;
 if(!check(stagePayloadUnverified(disk,device,2,output,8192,completed)&&completed==2&&verifyPayloadBlocks(output,8192,hashes),"quarantined stream then complete authentication"))return 1;
 output[4113]^=1;
 if(!check(!verifyPayloadBlocks(output,8192,hashes),"cached verification rejects corrupt staged byte"))return 1;
 if(!check(!verifyPayloadBlocks(output,8191,hashes)&&!verifyPayloadBlocks(nullptr,8192,hashes)&&!verifyPayloadBlocks(output,8192,nullptr),"cached verification rejects invalid spans"))return 1;
 device.fail=true;memset(output,0xcc,8192);
 if(!check(!stagePayloadUnverified(disk,device,2,output,8192,completed)&&completed==0&&output[0]==0xcc,"raw failed DMA never copied"))return 1;
 if(!check(!stagePayloadUnverified(disk,device,2,output,4096,completed)&&!stagePayloadUnverified(disk,device,0,output,8192,completed),"raw staging validates bounds"))return 1;
}
