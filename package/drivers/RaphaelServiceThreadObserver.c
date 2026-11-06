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
#include <arm/pmap/pmap_internal.h>
#include <ipc/ipc_space.h>
#include <ipc/ipc_entry.h>
#include <ipc/ipc_port.h>
#include <kern/ticket_lock.h>
extern pmap_paddr_t pmap_vtophys(pmap_t,addr64_t);
extern unsigned long gPhysBase,gPhysSize;
// Diagnostic lookup uses the pinned native pmap try-lock and page-table walker.
// Never spin on a foreign pmap while the sampler has disabled preemption.
// Keep the mapping locked through the physical copy; a busy pmap is explicit.
static bool user_frame(pmap_t pmap,uint64_t fp,uint64_t *next,uint64_t *lr,
                       volatile uint64_t *busy)
{
 if(!pmap_try_lock(pmap,PMAP_LOCK_SHARED)){*busy=1;return false;}
 uint64_t physical=pmap_vtophys(pmap,fp);bool copied=false;
 if(physical && physical>=gPhysBase && gPhysSize>=16 && physical-gPhysBase<=gPhysSize-16){
  const uint64_t *frame=(const uint64_t *)phystokv(physical);
  *next=frame[0];*lr=frame[1];copied=true;
 }
 pmap_unlock(pmap,PMAP_LOCK_SHARED);return copied;
}

// IPC_PEER_CAPTURE_BEGIN
// Called with preemption disabled on the sole enabled CPU and a referenced
// target thread. All acquired diagnostic locks are try-locks. The saved trap
// number alone may be stale: offline consumers must confirm the mach_msg2 PC.
static void capture_ipc_peer(thread_t target,task_t task,volatile uint64_t *out)
{
 if(!out[61] || (uint32_t)out[16]!=(uint32_t)-47)return;
 out[106]=0x31435049485052ULL;out[107]=1;
 out[108]=(uint32_t)out[18];out[112]=0xffffffff;
 out[121]=out[19]>>32;out[122]=out[15];out[123]=out[10];
 ipc_space_t space=task->itk_space;out[124]=(uintptr_t)space;
 if((out[15]&MACH_SEND_MSG) && out[108] && space){
  if(!lck_ticket_lock_try(&space->is_lock,&ipc_lck_grp))out[109]=2;
  else{
   if(!is_active(space))out[109]=3;
   else{
    ipc_entry_t entry=ipc_entry_lookup(space,(mach_port_name_t)out[108]);
    if(!entry)out[109]=4;
    else{
     out[111]=entry->ie_bits;
     if(!(IE_BITS_TYPE(entry->ie_bits)&MACH_PORT_TYPE_SEND_RIGHTS))out[109]=5;
     else{
      ipc_port_t port=(ipc_port_t)entry->ie_object;out[110]=(uintptr_t)port;
      if(!ip_mq_lock_try(port))out[109]=6;
      else{
       if(!ip_active(port))out[109]=7;
       else{
        ipc_space_t receiver=ip_get_receiver(port);
        out[113]=ip_get_receiver_name(port);out[114]=(uintptr_t)receiver;
        out[115]=ip_kotype(port);out[125]=port->ip_messages.imq_msgcount;
        out[109]=8;
        if(receiver && receiver->is_task){out[112]=(uint32_t)task_pid(receiver->is_task);out[109]=1;}
        else if(receiver==ipc_space_kernel)out[109]=9;
       }
       ip_mq_unlock(port);
      }
     }
    }
   }
   is_write_unlock(space);
  }
 }
 ipc_port_t reply=target->ith_special_reply_port;out[116]=(uintptr_t)reply;
 if(IP_VALID(reply)){
  if(!ip_mq_lock_try(reply))out[117]=2;
  else{
   out[117]=3;
   if(ip_active(reply) && reply->ip_specialreply){
    out[117]=1;out[118]=(uint32_t)ipc_special_reply_get_pid_locked(reply);
    out[119]=reply->ip_sync_link_state;out[120]=reply->ip_messages.imq_msgcount;out[127]=ip_get_receiver_name(reply);
    if(reply->ip_sync_link_state==PORT_SYNC_LINK_PORT)out[126]=(uintptr_t)reply->ip_sync_inheritor_port;
   }
   ip_mq_unlock(reply);
  }
 }
}
// IPC_PEER_CAPTURE_END

void raphael_service_thread_capture(thread_t target,volatile uint64_t *out)
{
 // References preserve thread lifetime. Only the boot CPU is enabled; prevent
 // rescheduling while copying a dormant thread's stack and original saved regs.
 task_t task=get_threadtask(target);pmap_t pmap=PMAP_NULL;
 // The diagnostic sampler must not wait for a target task's mutex.
 // A busy task keeps its raw register/kernel sample, with user unwind omitted.
 bool locked=task_lock_try(task);disable_preemption();
 if(locked){
  pmap=get_task_pmap(task);
  // Native ARM pmap_destroy drops a ledger reference on every call, even
  // when the pmap survives. pmap_reference alone does not retain that ledger.
  if(pmap){ledger_reference(pmap->ledger);pmap_reference(pmap);}
  out[58]=task->task_shared_region_slide;task_unlock(task);
 } else {out[58]=0xffffffff;out[62]=1;}
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
   uint64_t next,lr;if(!user_frame(pmap,fp,&next,&lr,out+63)){out[61]=3;break;}
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
 capture_ipc_peer(target,task,out);
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

// Resident-only interpretation of saved path arguments. A saved x16 may belong
// to an earlier trap; consumers must confirm the user PC is the matching syscall
// stub before interpreting this as a current filesystem operation.
void raphael_service_path_capture(thread_t target,const volatile uint64_t *sample,volatile uint64_t *out)
{
 uint64_t code=sample[16],address=0;
 out[0]=0x31544850485052ULL;out[1]=sample[1];out[2]=code;out[6]=sample[10];
 switch(code){
 case 5:case 33:case 58:case 136:case 188:case 190:case 220:case 338:case 340:case 398:address=sample[14];break;
 case 463:case 464:case 476:address=sample[15];break;
 default:return;
 }
 out[3]=address;
 if(address<4096 || address>=0x10000000000ULL){out[5]=6;return;}
 task_t task=get_threadtask(target);pmap_t pmap=PMAP_NULL;
 if(!task_lock_try(task)){out[5]=4;return;}
 disable_preemption();pmap=get_task_pmap(task);
 if(pmap){ledger_reference(pmap->ledger);pmap_reference(pmap);}task_unlock(task);
 uint8_t *dst=(uint8_t *)(out+8);unsigned done=0;out[5]=2;
 while(pmap && done<448){
  uint64_t at=address+done;unsigned n=4096-(unsigned)(at&4095);if(n>448-done)n=448-done;
  if(!pmap_try_lock(pmap,PMAP_LOCK_SHARED)){out[5]=5;break;}
  uint64_t physical=pmap_vtophys(pmap,at);
  if(!physical || physical<gPhysBase || gPhysSize<n || physical-gPhysBase>gPhysSize-n){pmap_unlock(pmap,PMAP_LOCK_SHARED);out[5]=3;break;}
  const uint8_t *src=(const uint8_t *)phystokv(physical);bool ended=false;
  for(unsigned i=0;i<n;++i){uint8_t ch=src[i];dst[done++]=ch;if(!ch){out[5]=1;ended=true;break;}}
  pmap_unlock(pmap,PMAP_LOCK_SHARED);if(ended)break;
 }
 if(!pmap)out[5]=3;out[4]=done;
 enable_preemption();if(pmap)pmap_destroy(pmap);
}
