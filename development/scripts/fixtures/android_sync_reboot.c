/* SPDX-License-Identifier: BSD-2-Clause-Patent */
/* Explicit recovery from an already stuck Android userspace reboot. */
#include <unistd.h>
#include <sys/reboot.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
 if(argc!=2||strcmp(argv[1],"--sync-and-reboot")||geteuid()!=0) return 2;
 sync();
 if(reboot(RB_AUTOBOOT)) {perror("reboot");return 1;}
 return 0;
}
