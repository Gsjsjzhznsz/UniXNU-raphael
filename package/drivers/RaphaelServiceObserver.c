// SPDX-License-Identifier: BSD-2-Clause-Patent
// Bounded read-only service snapshots at the diagnostic observer deadline.
#include <sys/param.h>
#include <sys/proc_internal.h>
#include <sys/user.h>
#include <sys/systm.h>
#include <sys/reason.h>
#include <kern/thread.h>
#include <kern/task.h>
#include <kern/sched_prim.h>
#include <arm/thread.h>
#include <mach/arm/thread_status.h>
#define PID_CAP 256
#define SERVICE_CAP 8
#define THREAD_CAP 8
#define THREAD_WORDS 128
#define SERVICE_WORDS (8+THREAD_CAP*THREAD_WORDS)
volatile uint64_t raphael_service_record_words=THREAD_WORDS;
volatile uint64_t raphael_service_header[8];
volatile uint64_t raphael_service_processes[PID_CAP][8];
volatile uint64_t raphael_service_threads[SERVICE_CAP][SERVICE_WORDS];
// Keep the original eight-slot ABI. A later/restarted display service may
// replace a lower-priority sample instead of being hidden by PID ordering.
static unsigned service_priority(const char *name)
{
 const char *names[]={"SpringBoard","lsd","containermanager","CommCenter","iconservicesagen","iconservicesd","backboardd","com.apple.datami","com.apple.migrat","online-auth-agen","amfid","misd","watchdogd","launchd","cfprefsd","usermanagerd","keybagd","configd","PreBoard"};
 for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i)if(!strcmp(name,names[i]))return i;
 return 255;
}
static unsigned service_slot(const char *name)
{
 unsigned count=(unsigned)raphael_service_header[4],priority=service_priority(name);
 if(priority==255)return SERVICE_CAP;
 if(count<SERVICE_CAP)return count;
 unsigned worst=0;
 for(unsigned i=1;i<SERVICE_CAP;++i)
  if(service_priority((const char *)&raphael_service_threads[i][4])>service_priority((const char *)&raphael_service_threads[worst][4]))worst=i;
 return priority<service_priority((const char *)&raphael_service_threads[worst][4])?worst:SERVICE_CAP;
}
extern void raphael_service_thread_capture(thread_t,volatile uint64_t *);
extern void raphael_service_kernel_probe_capture(void);
#if RAPHAEL_UFS_CONSOLE_LOG
static void persist_service_snapshot(void);
#endif

#if RAPHAEL_SERVICE_SPAWN_WAITS
// Independent record: do not consume the named-service slots or change their ABI.
// One referenced thread per proxy, at most 64 proxies from the existing PID scan.
#define SPAWN_CAP 64
#define SPAWN_WORDS (8+THREAD_WORDS)
volatile uint64_t raphael_service_spawn_header[8];
volatile uint64_t raphael_service_spawn_threads[SPAWN_CAP][SPAWN_WORDS];
static void capture_spawn_wait(proc_t p,pid_t pid,const char *name)
{
 if(strcmp(name,"xpcproxy"))return;
 ++raphael_service_spawn_header[3];
 unsigned slot=(unsigned)raphael_service_spawn_header[4];
 if(slot>=SPAWN_CAP)return;
 volatile uint64_t *out=raphael_service_spawn_threads[slot];
 out[0]=pid;memcpy((void *)&out[4],name,32);
 thread_t target=NULL;struct uthread *ut;
 proc_lock(p);
 TAILQ_FOREACH(ut,&p->p_uthlist,uu_list){
  if(target){out[2]=1;break;}
  target=get_machthread(ut);thread_reference(target);
 }
 proc_unlock(p);
 if(target){
  out[1]=1;raphael_service_thread_capture(target,out+8);
  thread_deallocate(target);
 }
 out[3]=2;raphael_service_spawn_header[4]=slot+1;
}
#endif
#if RAPHAEL_NATIVE_CONSOLE
extern void raphael_native_console_mark(unsigned);
#endif
void raphael_native_services_capture(void)
{
#if RAPHAEL_NATIVE_CONSOLE
 raphael_native_console_mark(2);
#endif
 raphael_service_kernel_probe_capture();
#if RAPHAEL_SERVICE_SPAWN_WAITS
 raphael_service_spawn_header[0]=0x31575053485052ULL;
 raphael_service_spawn_header[1]=1;raphael_service_spawn_header[2]=1;
 raphael_service_spawn_header[5]=SPAWN_CAP;
 raphael_service_spawn_header[6]=THREAD_WORDS;
 raphael_service_spawn_header[7]=SPAWN_WORDS;
#endif
 raphael_service_header[0]=0x31565253485052ULL;raphael_service_header[1]=1;
 raphael_service_header[5]=PID_CAP;raphael_service_header[6]=SERVICE_CAP;raphael_service_header[7]=THREAD_CAP;
 for(pid_t pid=1;pid<PID_CAP;++pid){
  raphael_service_header[2]=pid;
  proc_t p=proc_find(pid);if(!p)continue;
  unsigned index=(unsigned)raphael_service_header[3]++;
  volatile uint64_t *process=raphael_service_processes[index];process[0]=pid;process[1]=p->p_stat;
  char name[32]={0};strlcpy(name,p->p_comm,sizeof(name));memcpy((void *)&process[2],name,sizeof(name));
  unsigned slot=service_slot(pid==1?"launchd":name);
  if((pid==1 || service_priority(name)!=255) && slot<SERVICE_CAP){
   thread_t refs[THREAD_CAP]={0};unsigned count=0;struct uthread *ut;
   volatile uint64_t *out=raphael_service_threads[slot];
   for(unsigned i=0;i<raphael_service_header[3];++i)if(raphael_service_processes[i][6]==slot+1)raphael_service_processes[i][6]=0;
   memset((void *)out,0,sizeof(raphael_service_threads[slot]));
   out[0]=pid;memcpy((void *)&out[4],name,sizeof(name));
   // XNU proc_internal.h requires this list and lock rather than walking a
   // task pointer that an exec transition can swap out.
   proc_lock(p);
   TAILQ_FOREACH(ut,&p->p_uthlist,uu_list){
    if(count==THREAD_CAP){out[2]=1;break;}
    thread_t thread=get_machthread(ut);thread_reference(thread);refs[count++]=thread;
   }
   proc_unlock(p);out[1]=count;
   for(unsigned i=0;i<count;++i){raphael_service_thread_capture(refs[i],out+8+i*THREAD_WORDS);thread_deallocate(refs[i]);}
   out[3]=2;process[6]=slot+1;if(slot==raphael_service_header[4])raphael_service_header[4]=slot+1;
  }
#if RAPHAEL_SERVICE_SPAWN_WAITS
  capture_spawn_wait(p,pid,name);
#endif
  proc_rele(p);
 }
#if RAPHAEL_SERVICE_SPAWN_WAITS
 raphael_service_spawn_header[2]=2;
#endif
 raphael_service_header[1]=2;
#if RAPHAEL_UFS_CONSOLE_LOG
 persist_service_snapshot();
#endif
#if RAPHAEL_NATIVE_CONSOLE
 raphael_native_console_mark(3);
#endif
}


// Periodic LS progress: normal observer thread, separate from final eight slots.
#if RAPHAEL_UFS_CONSOLE_LOG
extern void raphael_ufs_log_snapshot(const char *,const volatile uint64_t *,unsigned);
extern volatile uint32_t raphael_native_root_limit;
void raphael_native_ls_progress(unsigned poll)
{
 static uint64_t last;
 static unsigned sequence;
 static uint64_t words[8+THREAD_CAP*THREAD_WORDS];
 uint64_t now,frequency;
 if(raphael_native_root_limit!=18000 || sequence>=16)return;
 __asm__ volatile("mrs %0,cntpct_el0":"=r"(now));
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(frequency));
 if(!frequency || frequency>1000000000ULL)return;
 if(!last){last=now;return;}
 if(now-last<frequency*120)return;
 last=now;memset(words,0,sizeof(words));
 words[0]=0x3150474c485052ULL;words[1]=1;words[2]=now;words[3]=frequency;words[7]=poll;
 for(pid_t pid=1;pid<PID_CAP;++pid){
  proc_t p=proc_find(pid);if(!p)continue;
  if(strcmp(p->p_comm,"lsd")){proc_rele(p);continue;}
  words[4]=pid;
  thread_t refs[THREAD_CAP]={0};unsigned count=0;struct uthread *ut;
  proc_lock(p);
  TAILQ_FOREACH(ut,&p->p_uthlist,uu_list){
   if(count==THREAD_CAP){words[6]=1;break;}
   thread_t target=get_machthread(ut);thread_reference(target);refs[count++]=target;
  }
  proc_unlock(p);proc_rele(p);words[5]=count;
  for(unsigned i=0;i<count;++i){raphael_service_thread_capture(refs[i],words+8+i*THREAD_WORDS);thread_deallocate(refs[i]);}
  break;
 }
 char name[32];snprintf(name,sizeof(name),"LS_PROGRESS_%02u",++sequence);
 raphael_ufs_log_snapshot(name,words,8+(unsigned)words[5]*THREAD_WORDS);
}
#endif
// End periodic LS progress.

// First real user exception per selected service, before original delivery.
// Later exceptions only increment the count; normal exception handling proceeds.
#define EXCEPTION_SLOTS 4
#define EXCEPTION_WORDS (16+THREAD_WORDS)
volatile uint64_t raphael_service_exceptions[EXCEPTION_SLOTS][EXCEPTION_WORDS];
void raphael_native_service_exception(thread_t target,int exception,const int64_t *code,unsigned count)
{
 if(!count || !code)return;
 proc_t p=proc_find(pid_from_task(get_threadtask(target)));if(!p)return;
 char name[32]={0};strlcpy(name,p->p_comm,sizeof(name));pid_t pid=proc_pid(p);proc_rele(p);
 const char *names[]={"SpringBoard","watchdogd","backboardd","liveactivitiesd"};
 for(unsigned slot=0;slot<EXCEPTION_SLOTS;++slot){
  if(strcmp(name,names[slot]))continue;
  volatile uint64_t *out=raphael_service_exceptions[slot];
  __atomic_fetch_add(&out[7],1,__ATOMIC_RELAXED);
  uint64_t empty=0;
  if(!__atomic_compare_exchange_n(&out[1],&empty,1,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return;
  out[0]=0x31584553504852ULL;out[2]=pid;out[3]=exception;out[4]=count;
  out[5]=code[0];out[6]=count>1?code[1]:0;memcpy((void *)&out[8],name,sizeof(name));
  raphael_service_thread_capture(target,out+16);
  __atomic_store_n(&out[1],2,__ATOMIC_RELEASE);return;
 }
}


// proc_exit owns the process lifetime. Only report committed original status
// and reason; printf uses the existing queue and never performs storage I/O.
extern unsigned int vm_page_free_count,vm_page_active_count,vm_page_inactive_count,vm_page_wire_count;
void raphael_native_service_exit(proc_t p)
{
 if(strcmp(p->p_comm,"backboardd") && strcmp(p->p_comm,"SpringBoard"))return;
 struct os_reason *reason=p->p_exit_reason;
 const char *description=exit_reason_get_string_desc(reason);
 printf("RPH SERVICE EXIT pid=%d name=%s status=%x reason_namespace=%u reason_code=%llu reason_flags=%llx free=%u active=%u inactive=%u wired=%u\n",
  proc_pid(p),p->p_comm,(unsigned)p->p_xstat,reason?reason->osr_namespace:0,
  reason?(unsigned long long)reason->osr_code:0,reason?(unsigned long long)reason->osr_flags:0,
  vm_page_free_count,vm_page_active_count,vm_page_inactive_count,vm_page_wire_count);
 printf("RPH SERVICE EXIT DESC pid=%d name=%s description=%.1024s\n",proc_pid(p),p->p_comm,description?description:"<none>");
}

// The target still has its original syscall reference and permission checks.
// Report the original sender and reason before unchanged signal delivery.
void raphael_native_service_terminate(proc_t caller,proc_t target,struct os_reason *reason)
{
 if(strcmp(target->p_comm,"backboardd") && strcmp(target->p_comm,"SpringBoard"))return;
 const char *description=exit_reason_get_string_desc(reason);
 printf("RPH SERVICE TERMINATE caller=%d caller_name=%s target=%d target_name=%s reason_namespace=%u reason_code=%llu description=%.1024s\n",
  proc_pid(caller),caller->p_comm,proc_pid(target),target->p_comm,
  reason?reason->osr_namespace:0,reason?(unsigned long long)reason->osr_code:0,
  description?description:"<none>");
}

#if RAPHAEL_UFS_CONSOLE_LOG
extern void raphael_ufs_log_snapshot(const char *,const volatile uint64_t *,unsigned);
extern volatile uint64_t raphael_service_kernel_probe[128];
extern volatile uint64_t raphael_native_watchdog_record[16],raphael_watchdog_client_record[16],raphael_watchdog_method_record[32];
extern volatile uint64_t raphael_native_root_record[16],raphael_native_user_record[16];
extern volatile unsigned raphael_display_clients;
extern volatile uint64_t raphael_display_validations,raphael_display_rejected,raphael_display_kicks;
extern volatile uint64_t raphael_display_frames,raphael_display_blank_frames,raphael_display_retired;
extern volatile uint64_t raphael_display_reject_reason,raphael_display_transfer_status,raphael_display_client_status,raphael_display_power_status;
extern volatile uint64_t raphael_display_bytes,raphael_display_nonblack;
static void persist_service_snapshot(void)
{
 uint64_t context[2];
 __asm__ volatile("mrs %0,cntpct_el0":"=r"(context[0]));
 __asm__ volatile("mrs %0,cntfrq_el0":"=r"(context[1]));
 uint64_t display[]={raphael_display_clients,raphael_display_validations,raphael_display_rejected,raphael_display_kicks,
  raphael_display_frames,raphael_display_blank_frames,raphael_display_retired,raphael_display_reject_reason,
  raphael_display_transfer_status,raphael_display_client_status,raphael_display_power_status,raphael_display_bytes,raphael_display_nonblack};
 raphael_ufs_log_snapshot("context",context,2);
 raphael_ufs_log_snapshot("display",display,sizeof(display)/sizeof(display[0]));
#define SAVE(name,count) raphael_ufs_log_snapshot("_" #name,(const volatile uint64_t *)(name),count)
 SAVE(raphael_native_watchdog_record,16);SAVE(raphael_watchdog_client_record,16);SAVE(raphael_watchdog_method_record,32);
 SAVE(raphael_native_root_record,16);SAVE(raphael_native_user_record,16);
 raphael_ufs_log_snapshot("_raphael_service_record_words",&raphael_service_record_words,1);
 SAVE(raphael_service_header,8);
 SAVE(raphael_service_processes,(unsigned)raphael_service_header[3]*8);
 SAVE(raphael_service_threads,(unsigned)raphael_service_header[4]*SERVICE_WORDS);
 SAVE(raphael_service_kernel_probe,128);SAVE(raphael_service_exceptions,EXCEPTION_SLOTS*EXCEPTION_WORDS);
#if RAPHAEL_SERVICE_SPAWN_WAITS
 SAVE(raphael_service_spawn_header,8);
 SAVE(raphael_service_spawn_threads,(unsigned)raphael_service_spawn_header[4]*SPAWN_WORDS);
#endif
#undef SAVE
}
#endif
