#!/usr/bin/env python3
"""Exercise the actual patched observer transition and strict wire decoder on host.
Counter reads and watchdog-expiry query are mocked; this is not handset proof.
"""
import datetime as dt, json, struct, subprocess, tempfile
from pathlib import Path
from entry_probe import ROOT,sha
from native_service_window import MAGIC,checkpoint_mode,decode_service_window

def main():
    review=json.loads((ROOT/'artifacts/service-startup-review/current.json').read_text())
    folder=ROOT/review['directory']
    before=folder/'bsd_init.first-method.c'
    patch=ROOT/'UniXNU-raphael/patches/xnu/raphael-watchdog-service-window.patch'
    out=ROOT/'artifacts/service-window-host'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='rph-service-window-') as tmp:
        target=Path(tmp)/'bsd/kern/bsd_init.c';target.parent.mkdir(parents=True);target.write_bytes(before.read_bytes())
        subprocess.run(['git','apply',str(patch)],cwd=tmp,check=True,capture_output=True)
        actual=target.read_text();start=actual.index('\t\t/* Explicit short service observation') if '\t\t/* Explicit short service observation' in actual else actual.index('/* Explicit short service observation')
        stop=actual.index('raphael_native_watchdog_pet();',start)
        logic=actual[start:stop]
        assert 'raphael_native_root_record[8]' not in logic
        logic=logic.replace('__asm__ volatile("isb\\n mrs %0,cntpct_el0" : "=r"(now));','now = mock_now;')
        logic=logic.replace('__asm__ volatile("mrs %0,cntfrq_el0" : "=r"(frequency));','frequency = mock_frequency;')
        assert '__asm__' not in logic
    c=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
volatile uint64_t raphael_watchdog_method_record[32];
volatile uint64_t raphael_watchdog_client_record[16];
volatile uint64_t raphael_native_service_window_record[8];
volatile uint64_t raphael_native_root_record[16];
volatile uint32_t raphael_native_service_window_seconds=5;
uint64_t mock_now, mock_frequency=19200000;
int mock_expired;
#define panic(message) abort()
int raphael_native_watchdog_observer_expired(void) { return mock_expired; }
static void step(unsigned i) {
 do {
LOGIC
 } while (0);
}
static void reset(void) {
 memset((void *)raphael_native_service_window_record,0,64);
 memset((void *)raphael_watchdog_method_record,0,256);
 memset((void *)raphael_watchdog_client_record,0,128);
 mock_expired=0;
}
int main(void) {
 reset(); mock_now=230*mock_frequency; step(1818);
 assert(raphael_native_service_window_record[0]==0);
 raphael_watchdog_method_record[1]=2;raphael_watchdog_method_record[2]=3;raphael_watchdog_client_record[4]=1;
 step(1818); assert(raphael_native_service_window_record[3]==mock_now);
 mock_now+=5*mock_frequency-1;step(1819);assert(raphael_native_service_window_record[4]==0);
 mock_now++;step(1820);assert(raphael_native_service_window_record[4]==mock_now);
 assert(raphael_native_root_record[2]==1821);
 assert(raphael_native_service_window_record[6]==3 && raphael_native_service_window_record[7]==1);
 reset();raphael_watchdog_method_record[1]=2;raphael_watchdog_method_record[2]=1;
 mock_now=300*mock_frequency;step(3000);assert(!raphael_native_service_window_record[4]);
 mock_now+=5*mock_frequency;mock_expired=1;step(3001);
 assert(!raphael_native_service_window_record[4]);
 puts("actual patched C: no premature stop, physical five seconds, late start, initial counters, observer-bound precedence passed");
 return 0;
}
'''
    source=out/'observer-host.c';source.write_text(c.replace('LOGIC',logic))
    command=['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(source),'-o',str(out/'observer-host')]
    p=subprocess.run(command,capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    p=subprocess.run([str(out/'observer-host')],capture_output=True,text=True);(out/'run.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    symbols={'_raphael_native_service_window_record':100,'_raphael_native_service_window_seconds':200}
    f=19200000;start=f*230;end=start+f*5
    budget=dict(counter_frequency=f,start_counter=f,stop_counter=end+100,deadline_ticks=f*420,observer_deadline_ticks=f*360)
    def decode(words):
        def read(at,n):return struct.pack('<I',5) if at==200 else struct.pack('<8Q',*words)
        return decode_service_window(read,symbols,budget,end+200)
    valid=[MAGIC,1,f,start,end,f*5,3,1]
    assert decode(valid)['elapsed_ms']==5000 and not decode([0]*8)['started']
    pending=valid[:];pending[4]=0;assert not decode(pending)['completed']
    rejected=0
    for index,value in [(0,0),(1,2),(2,1),(3,0),(4,end-1),(4,end+1000),(5,f*4),(6,0)]:
        row=valid[:];row[index]=value
        try:decode(row)
        except AssertionError:rejected+=1
        else:raise AssertionError(('invalid wire accepted',index))
    assert checkpoint_mode(4,lambda a,n:struct.pack('<I',5),symbols)=='first-method-plus-5s'
    for marker,seconds in [(4,250),(5,5)]:
        try:checkpoint_mode(marker,lambda a,n:struct.pack('<I',seconds),symbols)
        except AssertionError:rejected+=1
        else:raise AssertionError('invalid compiled mode accepted')
    report=dict(passed=True,handset_executed=False,actual_patched_c_tested=True,asan_ubsan=True,decoder_positive_inactive_pending=True,negative_decoder_cases=rejected,patch_sha256=sha(patch.read_bytes()),decoder_sha256=sha((ROOT/'scripts/native_service_window.py').read_bytes()),source_sha256=sha(source.read_bytes()),scope='Counter reads and expiry query mocked; actual C branch extracted from the patch applied to the successful frozen source. No watchdog MMIO or original userland execution.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(out);print(p.stdout.strip());print('Decoder negative cases:',rejected)
if __name__=='__main__':main()
