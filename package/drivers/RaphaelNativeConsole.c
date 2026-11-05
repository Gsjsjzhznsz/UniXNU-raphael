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
 if((poll%100)==1)printf("RPH UFS READ requests=%llu bytes=%llu failures=%llu commands=%llu blocks=%llu\n",raphael_ufs_requests,raphael_ufs_bytes,raphael_ufs_failures,raphael_ufs_read_commands,raphael_ufs_read_blocks);
 if((poll%100)==1)printf("RPH RAM DATA resident=%llu reads=%llu writes=%llu failures=%llu zero_write_bytes=%llu\n",native_ram_block_resident_bytes,native_ram_block_reads,native_ram_block_writes,native_ram_block_failures,native_ram_block_zero_write_bytes);
 if((poll%100)==1)printf("RPH VM pages free=%u active=%u inactive=%u wired=%u\n",vm_page_free_count,vm_page_active_count,vm_page_inactive_count,vm_page_wire_count);
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
