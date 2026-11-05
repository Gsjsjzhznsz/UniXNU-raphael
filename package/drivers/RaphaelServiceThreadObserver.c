// SPDX-License-Identifier: BSD-2-Clause-Patent
// Compiled using the original OSFMK startup recipe and original thread ABI.
#include <kern/thread.h>
#include <kern/task.h>
#include <kern/ledger.h>
#include <kern/clock.h>
#include <kern/sched_prim.h>
#include <arm/thread.h>
#include <machine/machine_routines.h>
#include <mach/arm/thread_status.h>
#include <vm/pmap.h>
extern unsigned long gPhysBase,gPhysSize;
// Only already mapped user stack pages inside the admitted RAM grant.
static bool user_frame(pmap_t pmap,uint64_t fp,uint64_t *next,uint64_t *lr)
{
 ppnum_t ppn=pmap_find_phys(pmap,fp);if(!ppn)return false;
 uint64_t physical=((uint64_t)ppn<<12)+(fp&4095);
 if(physical<gPhysBase || gPhysSize<16 || physical-gPhysBase>gPhysSize-16)return false;
 const uint64_t *frame=(const uint64_t *)phystokv(physical);*next=frame[0];*lr=frame[1];return true;
}
void raphael_service_thread_capture(thread_t target,volatile uint64_t *out)
{
 // References preserve thread lifetime. Only the boot CPU is enabled; prevent
 // rescheduling while copying a dormant thread's stack and original saved regs.
 task_t task=get_threadtask(target);pmap_t pmap=PMAP_NULL;
 task_lock(task);disable_preemption();
 pmap=get_task_pmap(task);if(pmap)pmap_reference(pmap);
 out[58]=task->task_shared_region_slide;task_unlock(task);
 out[0]=(uintptr_t)target;out[1]=thread_tid(target);out[2]=target->state;
 out[3]=target->wait_event;out[4]=(uintptr_t)target->continuation;
 out[5]=target->kernel_stack;out[6]=kernel_stack_size;
 arm_saved_state_t *user=get_user_regs(target);
 if(user && is_saved_state64(user)){
  out[10]=get_saved_state_pc(user);out[11]=get_saved_state_lr(user);
  out[12]=get_saved_state_sp(user);out[13]=get_saved_state_cpsr(user);
  const unsigned regs[]={0,1,16,2,3,4,5};
  for(unsigned i=0;i<7;++i)out[14+i]=get_saved_state_reg(user,regs[i]);
  out[56]=get_saved_state_reg(user,6);out[57]=get_saved_state_reg(user,7);
  out[59]=get_saved_state_fp(user);out[61]=1;
  uint64_t fp=out[59],sp=out[12];
  for(unsigned i=0;pmap && i<16;++i){
   if((fp&15) || sp>=0x10000000000ULL || fp<sp || fp-sp>1048576){out[61]=2;break;}
   uint64_t next,lr;if(!user_frame(pmap,fp,&next,&lr)){out[61]=3;break;}
   out[64+i*2]=fp;out[65+i*2]=lr;out[60]=i+1;
   if(next<=fp)break;fp=next;
  }
 }
 if(target!=current_thread() && target->kernel_stack && kernel_stack_size>=4096 && kernel_stack_size<=65536){
  arm_kernel_saved_state_t *saved=&thread_get_kernel_state(target)->machine.ss;
  out[7]=saved->sp;out[8]=saved->fp;out[9]=saved->lr;out[22]=1;
  uintptr_t fp=saved->fp;
  for(unsigned i=0;i<16;++i){
   if((fp&15) || fp<target->kernel_stack || fp>target->kernel_stack+kernel_stack_size-16)break;
   const uint64_t *frame=(const uint64_t *)fp;
   out[24+i*2]=fp;out[25+i*2]=frame[1];out[21]=i+1;
   if(frame[0]<=fp)break;fp=frame[0];
  }
 }
 // The referenced thread owns this ledger until teardown. Single-CPU capture
 // remains nonpreemptible; these APIs only read existing ledger accounting.
 if(target->t_threadledger && thread_ledgers.cpu_time>=0){
  struct ledger_entry_info info={0};int actions=0;
  ledger_get_entry_info(target->t_threadledger,thread_ledgers.cpu_time,&info);
  if(ledger_get_actions(target->t_threadledger,thread_ledgers.cpu_time,&actions)==KERN_SUCCESS){
   out[96]=0x314c4454485052ULL;out[97]=target->options;
   out[98]=info.lei_limit;out[99]=(uint64_t)info.lei_balance;
   out[100]=(uint64_t)info.lei_credit;out[101]=(uint64_t)info.lei_debit;
   out[102]=info.lei_refill_period;out[103]=info.lei_last_refill;
   out[104]=(uint32_t)actions;out[105]=mach_absolute_time();
  }
 }
 enable_preemption();if(pmap)pmap_destroy(pmap);
}

volatile uint64_t raphael_service_kernel_probe[128];
void raphael_service_kernel_probe_capture(void)
{
 thread_t target=THREAD_NULL,thread;
 task_lock(kernel_task);
 queue_iterate(&kernel_task->threads,thread,thread_t,task_threads){
  if(thread!=current_thread() && thread->kernel_stack){target=thread;thread_reference(target);break;}
 }
 task_unlock(kernel_task);
 if(target){raphael_service_thread_capture(target,raphael_service_kernel_probe);thread_deallocate(target);}
}
