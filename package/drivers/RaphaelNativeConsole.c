// SPDX-License-Identifier: BSD-2-Clause-Patent
// Explicit handset diagnostic: reuse the initialized original video console.
#include <kern/thread.h>
#include <kern/misc_protos.h>
#include <pexpert/pexpert.h>
extern void vcputc(char);
extern volatile uint32_t raphael_native_root_stage,raphael_native_init_stage;
extern volatile uint64_t raphael_native_user_record[],raphael_watchdog_method_record[];
extern volatile uint64_t raphael_display_frames,raphael_display_client_status;
extern volatile unsigned raphael_display_stage,raphael_display_clients;
volatile uint64_t raphael_native_console_record[8];
#if RAPHAEL_UFS_CONSOLE_LOG
extern void raphael_ufs_log_capture(const char *,int);
extern unsigned int vm_page_free_count,vm_page_active_count,vm_page_inactive_count,vm_page_wire_count;
extern void raphael_ufs_log_flush(void);
extern void raphael_native_ls_progress(unsigned);
extern void raphael_ufs_log_init(void);
extern volatile uint64_t raphael_ufs_console_log_record[];
// Native console requires handset display and its sparse Data profile.
extern volatile uint64_t native_ram_block_resident_bytes,native_ram_block_reads,native_ram_block_writes,native_ram_block_failures,native_ram_block_zero_write_bytes;
extern volatile uint64_t raphael_ufs_requests,raphael_ufs_bytes,raphael_ufs_failures,raphael_ufs_read_commands,raphael_ufs_read_blocks;
// Native VFS scalar counters: sampled without taking filesystem locks.
extern int desiredvnodes,desiredNodes,nc_disabled;
extern long numvnodes,freevnodes,deadvnodes,numcache,num_recycledvnodes;
#include "RaphaelFrameProbe.h"
extern int raphael_display_copy_thumbnail(unsigned char *,unsigned,uint64_t [5]);
extern volatile uint64_t raphael_display_copy_ticks,raphael_display_copy_max_ticks,raphael_display_console_released;
extern volatile uint64_t raphael_ufs_read_ticks,raphael_ufs_verify_ticks,raphael_ufs_publish_ticks,raphael_ufs_max_chunk_ticks;
static void frame_thumbnail(void){
 static unsigned char rgb[RPH_FRAME_BYTES];static uint64_t last_frame;
 uint64_t meta[5];char row[600];const char hex[]="0123456789abcdef";
 if(!raphael_display_copy_thumbnail(rgb,sizeof(rgb),meta)||meta[0]==last_frame)return;
 int n=snprintf(row,sizeof(row),"\nRPH FRAME BEGIN frame=%llu counter=%llu width=%u height=%u nonblack=%llu fb_nonblack=%llu mismatches=%llu\n",
 meta[0],meta[1],RPH_FRAME_W,RPH_FRAME_H,meta[2],meta[3],meta[4]);raphael_ufs_log_capture(row,n);
 for(unsigned y=0;y<RPH_FRAME_H;++y){
  n=snprintf(row,sizeof(row),"\nRPH FRAME ROW %llu %u ",meta[0],y);
  for(unsigned x=0;x<RPH_FRAME_W*3;++x){unsigned b=rgb[y*RPH_FRAME_W*3+x];row[n++]=hex[b>>4];row[n++]=hex[b&15];}
  row[n++]='\n';raphael_ufs_log_capture(row,n);
  if((y%16)==15)raphael_ufs_log_flush();
 }
 n=snprintf(row,sizeof(row),"\nRPH FRAME END %llu\n",meta[0]);raphael_ufs_log_capture(row,n);raphael_ufs_log_flush();last_frame=meta[0];
}

#endif
static void line(const char *s) {
#if RAPHAEL_UFS_CONSOLE_LOG
 const char *end=s;while(*end)++end;raphael_ufs_log_capture(s,(int)(end-s));
#endif
 while(*s){if(*s=='\n')vcputc('\r');vcputc(*s++);}__asm__ volatile("dsb sy" ::: "memory");}
void raphael_native_console_begin(void)
{
#if RAPHAEL_UFS_CONSOLE_LOG
 raphael_ufs_log_init();
#endif
 initialize_screen(NULL,kPETextScreen);
 raphael_native_console_record[0]=1;
 line("\nRAPHAEL NATIVE XNU: LIVE CONSOLE\n");
 printf("RAPHAEL native console enabled; original services unchanged\n");
}
void raphael_native_console_tick(unsigned poll)
{
 raphael_native_console_record[1]=poll;
#if RAPHAEL_UFS_CONSOLE_LOG
 raphael_ufs_log_flush();
 raphael_native_ls_progress(poll);
 if((poll%100)==1)frame_thumbnail();
 if((poll%100)==1)printf("RPH UFS READ requests=%llu bytes=%llu failures=%llu commands=%llu blocks=%llu\n",raphael_ufs_requests,raphael_ufs_bytes,raphael_ufs_failures,raphael_ufs_read_commands,raphael_ufs_read_blocks);
 if((poll%100)==1)printf("RPH DISPLAY COPY ticks=%llu max_ticks=%llu console_released=%llu\n",raphael_display_copy_ticks,raphael_display_copy_max_ticks,raphael_display_console_released);
 if((poll%100)==1)printf("RPH UFS TIME read_ticks=%llu verify_ticks=%llu publish_ticks=%llu max_chunk_ticks=%llu\n",raphael_ufs_read_ticks,raphael_ufs_verify_ticks,raphael_ufs_publish_ticks,raphael_ufs_max_chunk_ticks);
 if((poll%100)==1)printf("RPH RAM DATA allocated=%llu pageable=1 reads=%llu writes=%llu failures=%llu zero_write_bytes=%llu\n",native_ram_block_resident_bytes,native_ram_block_reads,native_ram_block_writes,native_ram_block_failures,native_ram_block_zero_write_bytes);
 if((poll%100)==1)printf("RPH VM pages free=%u active=%u inactive=%u wired=%u\n",vm_page_free_count,vm_page_active_count,vm_page_inactive_count,vm_page_wire_count);
 if((poll%100)==1)printf("RPH VFS desired=%d vnodes=%ld free=%ld dead=%ld names=%ld name_limit=%d disabled=%d recycled=%ld\n",desiredvnodes,numvnodes,freevnodes,deadvnodes,numcache,desiredNodes,nc_disabled,num_recycledvnodes);
 if((poll%100)==1)printf("RPH UFS LOG blocks=%llu bytes=%llu dropped=%llu state=%llu error=%llx\n",raphael_ufs_console_log_record[3],raphael_ufs_console_log_record[4],raphael_ufs_console_log_record[5],raphael_ufs_console_log_record[1],raphael_ufs_console_log_record[6]);
#endif
 printf("RPH tick=%u root=%u init=%u syscalls=%llu wd=%llu display=%u clients=%u status=%llx frames=%llu\n",
 poll,raphael_native_root_stage,raphael_native_init_stage,raphael_native_user_record[1],
 raphael_watchdog_method_record[1],raphael_display_stage,raphael_display_clients,
 raphael_display_client_status,raphael_display_frames);
}
void raphael_native_console_mark(unsigned stage)
{
 raphael_native_console_record[2]=stage;
 if(stage==1)line("\nRAPHAEL: OBSERVER STOP; INIT STACK SNAPSHOT BEGIN\n");
 if(stage==2)line("\nRAPHAEL: SERVICE SNAPSHOT BEGIN\n");
 if(stage==3)line("\nRAPHAEL: SERVICE SNAPSHOT DONE; RETURNING\n");
#if RAPHAEL_UFS_CONSOLE_LOG
 raphael_ufs_log_flush();
#endif
}
