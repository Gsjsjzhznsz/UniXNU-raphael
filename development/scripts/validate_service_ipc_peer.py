from pathlib import Path
import argparse
import datetime as dt
import json
import os
import struct
import subprocess
import sys

r = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description='Validate actual nonblocking IPC peer helper and thread decoder; no device I/O.')
ap.add_argument('--out', type=Path)
args = ap.parse_args()
out = args.out or r / 'artifacts/service-ipc-peer-host' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out.mkdir(parents=True, exist_ok=True)
source = (r / 'UniXNU-raphael/package/drivers/RaphaelServiceThreadObserver.c').read_text()
code = source.split('// IPC_PEER_CAPTURE_BEGIN', 1)[1].split('// IPC_PEER_CAPTURE_END', 1)[0]
prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t mach_port_name_t;
struct fake_task;
struct fake_space { int is_lock; bool active; struct fake_task *is_task; };
struct fake_port {
 bool busy,locked,active,ip_specialreply; int copyout_pid,ip_sync_link_state,kotype;
 struct fake_space *receiver; uint32_t receiver_name;
 struct { uint32_t imq_msgcount; } ip_messages;
 struct fake_port *ip_sync_inheritor_port;
};
struct fake_entry { uint32_t ie_bits; void *ie_object; };
struct fake_task { struct fake_space *itk_space; int pid; };
struct fake_thread { struct fake_port *ith_special_reply_port; };
typedef struct fake_task *task_t;
typedef struct fake_thread *thread_t;
typedef struct fake_space *ipc_space_t;
typedef struct fake_port *ipc_port_t;
typedef struct fake_entry *ipc_entry_t;
static struct fake_space sender,receiver,kernel;
static struct fake_task owner,peer;
static struct fake_thread thread;
static struct fake_entry entry;
static struct fake_port remote,reply;
static int ipc_lck_grp,held,lookups,port_locks;
static bool missing;
static ipc_space_t ipc_space_kernel=&kernel;
#define MACH_SEND_MSG 1
#define MACH_PORT_TYPE_SEND_RIGHTS 3
#define PORT_SYNC_LINK_PORT 1
#define IE_BITS_TYPE(x) (x)
#define IP_VALID(x) ((x)!=NULL)
static bool lck_ticket_lock_try(int *lock,int *group){assert(group==&ipc_lck_grp);if(*lock)return false;*lock=1;held++;return true;}
static bool is_active(ipc_space_t space){assert(space->is_lock);return space->active;}
static ipc_entry_t ipc_entry_lookup(ipc_space_t space,mach_port_name_t name){assert(space->is_lock && space->active && name==0xe207);lookups++;return missing?NULL:&entry;}
static bool ip_mq_lock_try(ipc_port_t port){assert(port);port_locks++;if(port->busy)return false;assert(!port->locked);port->locked=true;held++;return true;}
static bool ip_active(ipc_port_t port){assert(port->locked);return port->active;}
static ipc_space_t ip_get_receiver(ipc_port_t port){assert(port->locked && port->active);return port->receiver;}
static uint32_t ip_get_receiver_name(ipc_port_t port){assert(port->locked && port->active);return port->receiver_name;}
static int ip_kotype(ipc_port_t port){assert(port->locked && port->active);return port->kotype;}
static int task_pid(task_t task){assert(remote.locked);return task->pid;}
static void ip_mq_unlock(ipc_port_t port){assert(port->locked);port->locked=false;held--;}
static void is_write_unlock(ipc_space_t space){assert(space->is_lock);space->is_lock=0;held--;}
static int ipc_special_reply_get_pid_locked(ipc_port_t port){assert(port->locked && port->active && port->ip_specialreply);return port->copyout_pid;}
'''
suffix = r'''
int main(int argc,char **argv){
 assert(argc==2);FILE *file=fopen(argv[1],"wb");assert(file);
 for(unsigned test=0;test<18;test++){
  uint64_t sample[130]={0},before[106];
  sender=(struct fake_space){0,true,&owner};receiver=(struct fake_space){0,true,&peer};kernel=(struct fake_space){0,true,NULL};
  owner=(struct fake_task){&sender,62};peer=(struct fake_task){&receiver,42};
  remote=(struct fake_port){.active=true,.receiver=&receiver,.receiver_name=0x7703,.kotype=0,.ip_messages={1}};
  reply=(struct fake_port){.active=true,.ip_specialreply=true,.copyout_pid=99,.ip_sync_link_state=1,.receiver_name=0x6603,.ip_messages={0},.ip_sync_inheritor_port=&remote};
  entry=(struct fake_entry){1,&remote};thread.ith_special_reply_port=&reply;
  missing=false;held=lookups=port_locks=0;
  sample[61]=1;sample[16]=(uint32_t)-47;sample[15]=3;sample[18]=0xe207;sample[19]=(uint64_t)1203<<32;sample[10]=0x1e1b30b58;sample[20]=(uint64_t)0x6603<<32;
  sample[128]=0x12345678;sample[129]=0x87654321;
  if(test==1)sample[16]=5;
  if(test==2)sample[61]=0;
  if(test==3)sample[15]=2;
  if(test==4)sender.is_lock=1;
  if(test==5)sender.active=false;
  if(test==6)missing=true;
  if(test==7)entry.ie_bits=4;
  if(test==8)remote.busy=true;
  if(test==9)remote.active=false;
  if(test==10)remote.receiver=NULL;
  if(test==11)remote.receiver=&kernel;
  if(test==12)receiver.is_task=NULL;
  if(test==13)reply.busy=true;
  if(test==14)reply.active=false;
  if(test==15)reply.ip_specialreply=false;
  if(test==16)thread.ith_special_reply_port=NULL;
  if(test==17)owner.itk_space=NULL;
  memcpy(before,sample,sizeof(before));capture_ipc_peer(&thread,&owner,sample);
  assert(!held && !remote.locked && !reply.locked);
  assert(!memcmp(before,sample,sizeof(before)) && sample[128]==0x12345678 && sample[129]==0x87654321);
  assert(sender.is_lock==(test==4));
  if(test==1 || test==2){assert(!sample[106] && !lookups && !port_locks);}
  else{
   assert(sample[106]==0x31435049485052ULL && sample[107]==1 && sample[121]==1203 && sample[123]==sample[10]);
   const unsigned status[18]={1,0,0,0,2,3,4,5,6,7,8,9,8,1,1,1,1,0};
   assert(sample[109]==status[test]);
   if(test==0){assert(sample[112]==42 && sample[113]==0x7703 && sample[125]==1 && sample[118]==99 && sample[126]==(uintptr_t)&remote);}
   if(test==13)assert(sample[117]==2);
   if(test==14 || test==15)assert(sample[117]==3);
   if(test==16)assert(!sample[117] && !sample[116]);
  }
  assert(fwrite(sample,1024,1,file)==1);
 }
 assert(!fclose(file));return 0;
}
'''
fixture = out / 'ipc-peer-host.c'
fixture.write_text(prefix + code + suffix)
env = dict(os.environ, PATH='/opt/unixnu-linux/bin:/usr/bin:/bin', ASAN_OPTIONS='detect_leaks=1', UBSAN_OPTIONS='halt_on_error=1')
cmd = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-pie', '-no-pie', str(fixture), '-o', str(out / 'ipc-peer-host')]
subprocess.run(cmd, check=True, env=env)
subprocess.run([str(out / 'ipc-peer-host'), str(out / 'ipc-peer-samples.bin')], check=True, env=env)
sys.path.insert(0, str(r / 'scripts'))
from native_early import decode_service_thread
raw = (out / 'ipc-peer-samples.bin').read_bytes()
decoded = []
for n in range(18):
    words = struct.unpack_from('<128Q', raw, n*1024)
    row = decode_service_thread(words, 128, lambda _: None)
    assert ('ipc_wait_candidate' in row) == (n not in (1, 2))
    decoded.append(row.get('ipc_wait_candidate'))
assert decoded[0]['receiver_pid'] == 42 and decoded[0]['reply_send_once_copyout_pid'] == 99
assert decoded[0]['special_reply_receive_name'] == decoded[0]['saved_receive_name'] == 0x6603
assert decoded[11]['receiver_pid'] == -1
assert 'ipc_wait_candidate' not in decode_service_thread([0]*128, 128, lambda _: None)
rejections = []
for index, value in [(107, 2), (109, 10), (117, 4)]:
    words = list(struct.unpack_from('<128Q', raw))
    words[index] = value
    try:
        decode_service_thread(words, 128, lambda _: None)
    except AssertionError:
        rejections.append(index)
    else:
        raise AssertionError('Accepted malformed IPC telemetry')
(out / 'host-result.json').write_text(json.dumps(dict(
    passed=True, actual_helper_asan_ubsan_cases=18, decoder_cases=18, decoder_rejections=rejections,
    original_thread_prefix_unchanged=True, lock_release_and_busy_paths=True,
    handset_executed=False, scope='Mock IPC objects test actual helper branches and decoder; real scheduler and runtime endpoint identities remain unverified.'
), indent=2) + '\n')
print('IPC helper18 cases, original128-word ABI, decoder18 cases/3 malformed records, ASan/UBSan passed.')
