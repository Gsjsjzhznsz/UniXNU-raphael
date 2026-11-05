/* Explicit ephemeral original default /var seeding through the real BSD/APFS path.
 * File bytes and inode metadata are generated privately from the selected OS.
 */
#include <sys/types.h>
#include <sys/proc.h>
#include <sys/sysproto.h>
#include <sys/systm.h>
#include <sys/errno.h>
#include <sys/fcntl.h>
#include <sys/stat.h>
#include "seed_entries.h"
extern const unsigned char raphael_default_var_payload[];
/* The optional persistent UFS provider is absent in this emulator. No disk
 * store is opened; calls below report absence/failure, never successful I/O. */
unsigned native_ufs_store_mode(void); unsigned native_ufs_store_gpt_check(void);
int native_ufs_store_open(uint64_t,uint64_t *,const char **);
int native_ufs_store_read(uint64_t,uint32_t,void *);
int native_ufs_store_write(uint64_t,uint32_t,const void *);
int native_ufs_store_sync(void);
unsigned native_ufs_store_mode(void) {return 0;}
unsigned native_ufs_store_gpt_check(void) {return 0xff;}
int native_ufs_store_open(uint64_t n,uint64_t *first,const char **why) {(void)n;*first=0;*why="No persistent store in explicit ephemeral scratch mode";return 0;}
int native_ufs_store_read(uint64_t b,uint32_t n,void *d) {(void)b;(void)n;(void)d;return 0;}
int native_ufs_store_write(uint64_t b,uint32_t n,const void *d) {(void)b;(void)n;(void)d;return 0;}
int native_ufs_store_sync(void) {return 0;}
volatile int raphael_data_seed_status = -1;
volatile unsigned raphael_data_seed_entries = 0;
volatile unsigned raphael_data_seed_index = 0;
volatile uint64_t raphael_data_seed_written = 0;
volatile uint64_t raphael_data_seed_readback = 0;
void raphael_data_seed_checkpoint(int error);
__attribute__((noinline)) void raphael_data_seed_checkpoint(int error)
{
 __asm__ volatile("" : : "r"(error) : "memory");
}
int raphael_seed_default_var(proc_t p, user_addr_t scratch);
int raphael_seed_default_var(proc_t p, user_addr_t scratch)
{
 int error=0, result=0, fd=-1;
 /* Only owner-union mode uses this helper: its envp is USER_ADDR_NULL.
  * Paths occupy [0,1024), link targets [1024,2048), I/O [2048,3072).
  * load_init_program builds new argv in this same page after we return.
  */
 unsigned char verify[1024];
 for (unsigned i=0;i<sizeof(seed_entries)/sizeof(seed_entries[0]);i++) {
  const struct seed_entry *entry=&seed_entries[i];raphael_data_seed_index=i;
  if (strncmp(entry->path,"/private/var",12) ||
      (entry->path[12] && entry->path[12]!='/') || strlen(entry->path)>=1024) {error=EINVAL;goto done;}
  if ((error=copyout(entry->path,scratch,strlen(entry->path)+1))) goto done;
  if (entry->kind==1) {
   if (strcmp(entry->path,"/private/var")) {
    struct mkdir_args a={.path=scratch,.mode=0700};
    if ((error=mkdir(p,&a,&result))) goto done;
   }
  } else if (entry->kind==2) {
   struct open_args a={.path=scratch,.flags=O_WRONLY|O_CREAT|O_EXCL,.mode=0600};
   if ((error=open(p,&a,&fd))) goto done;
   for (uint64_t at=0;at<entry->length;) {
    size_t count=MIN((uint64_t)sizeof(verify),entry->length-at);
    if ((error=copyout(raphael_default_var_payload+entry->offset+at,scratch+2048,count))) goto done;
    struct write_args w={.fd=fd,.cbuf=scratch+2048,.nbyte=count};user_ssize_t wrote=0;
    if ((error=write(p,&w,&wrote))) goto done;
    if (wrote<=0 || (uint64_t)wrote>count) {error=EIO;goto done;}
    at+=wrote;raphael_data_seed_written+=wrote;
   }
   struct close_args c={.fd=fd};error=sys_close(p,&c,&result);fd=-1;if (error) goto done;
   a.flags=O_RDONLY;a.mode=0;if ((error=open(p,&a,&fd))) goto done;
   for (uint64_t at=0;at<entry->length;) {
    size_t count=MIN((uint64_t)sizeof(verify),entry->length-at);
    struct read_args r={.fd=fd,.cbuf=scratch+2048,.nbyte=count};user_ssize_t got=0;
    if ((error=read(p,&r,&got))) goto done;
    if (got<=0 || (uint64_t)got>count) {error=EIO;goto done;}
    if ((error=copyin(scratch+2048,verify,got))) goto done;
    if (memcmp(verify,raphael_default_var_payload+entry->offset+at,got)) {error=EIO;goto done;}
    at+=got;raphael_data_seed_readback+=got;
   }
   c.fd=fd;error=sys_close(p,&c,&result);fd=-1;if (error) goto done;
  } else if (entry->kind==3) {
   if (strlen(entry->target)>=1024) {error=ENAMETOOLONG;goto done;}
   if ((error=copyout(entry->target,scratch+1024,strlen(entry->target)+1))) goto done;
   struct symlink_args a={.path=scratch+1024,.link=scratch};
   if ((error=symlink(p,&a,&result))) goto done;
  } else {error=EINVAL;goto done;}
  struct lchown_args own={.path=scratch,.owner=entry->uid,.group=entry->gid};
  if ((error=lchown(p,&own,&result))) goto done;
  if (entry->kind!=3) {
   struct chmod_args bits={.path=scratch,.mode=entry->mode&07777};
   if ((error=chmod(p,&bits,&result))) goto done;
  }
  raphael_data_seed_entries++;
 }
 done:
 if (fd>=0) {struct close_args c={.fd=fd};sys_close(p,&c,&result);}
 raphael_data_seed_status=error;raphael_data_seed_checkpoint(error);return error;
}
