#!/usr/bin/env python3
import numpy as np
import csv
import json
import sys
import argparse
import multiprocessing as mp
import glob
import os
from functools import partial
from sofa_print import *
import subprocess
from time import sleep, time


def sofa_record(command, logdir, cfg):

    p_tcpdump = None
    p_mpstat  = None
    p_vmstat  = None
    p_nvsmi   = None
    p_nvtopo  = None 

    print_info('SOFA_COMMAND: %s' % command)
    sample_freq = 99
    if int(open("/proc/sys/kernel/kptr_restrict").read()) != 0:
        print_error(
            "/proc/kallsyms permission is restricted, please try the command below:")
        print_error("sudo sysctl -w kernel.kptr_restrict=0")
        quit()

    if int(open("/proc/sys/kernel/perf_event_paranoid").read()) != -1:
        print_error('PerfEvent is not avaiable, please try the command below:')
        print_error('sudo sysctl -w kernel.perf_event_paranoid=-1')
        quit()

    if subprocess.call(['mkdir', '-p', logdir]):
        quit()
    subprocess.call('rm %s/perf.data > /dev/null 2> /dev/null' % logdir, shell=True )
    subprocess.call('rm %s/sofa.pcap > /dev/null 2> /dev/null' % logdir, shell=True)
    subprocess.call('rm %s/gputrace*.nvvp > /dev/null 2> /dev/null' % logdir, shell=True)
    subprocess.call('rm %s/gputrace.tmp > /dev/null 2> /dev/null' % logdir, shell=True)
    subprocess.call('rm %s/*.csv > /dev/null 2> /dev/null' % logdir, shell=True)
    subprocess.call('rm %s/*.txt > /dev/null 2> /dev/null' % logdir, shell=True)
    try:
        print_info("Prolog of Recording...")
        with open(os.devnull, 'w') as FNULL:
           p_tcpdump =  subprocess.Popen(["tcpdump",
                              '-i',
                              'any',
                              '-v',
                              'tcp',
                              '-w',
                              '%s/sofa.pcap' % logdir],
                             stderr=FNULL)
        with open('%s/mpstat.txt' % logdir, 'w') as logfile:
            p_mpstat = subprocess.Popen(
                ['mpstat', '-P', 'ALL', '1', '600'], stdout=logfile)
        with open('%s/vmstat.txt' % logdir, 'w') as logfile:
            p_vmstat = subprocess.Popen(['vmstat', '-w', '1', '600'], stdout=logfile)
        if int(os.system('command -v nvprof')) == 0:
            with open('%s/nvsmi.txt' % logdir, 'w') as logfile:
                p_nvsmi = subprocess.Popen(['nvidia-smi', 'dmon', '-s', 'u'], stdout=logfile)
            with open('%s/nvlink_topo.txt' % logdir, 'w') as logfile:
                p_nvtopo = subprocess.Popen(['nvidia-smi', 'topo', '-m'], stdout=logfile)  
        with open('%s/sofa_time.txt' % logdir, 'w') as logfile:
            logfile.write(str(int(time()))+'\n')

        print_info("Recording...")

        if cfg.profile_all_cpus == True:
            perf_options = '-a'
        else:
            perf_options = ''

            
        subprocess.call('cp /proc/kallsyms %s/' % (logdir), shell=True )
        subprocess.call('chmod +w %s/kallsyms' % (logdir), shell=True )
        if int(os.system('command -v nvprof')) == 0:
            profile_command = 'nvprof --profile-child-processes -o %s/gputrace%%p.nvvp perf record -e cycles,bus-cycles -o %s/perf.data -F %s %s -- %s ' % (logdir, logdir, sample_freq, perf_options, command)
        else:
            print_warning('Profile without NVPROF')
            profile_command = 'perf record -o %s/perf.data -e cycles,bus-cycles -F %s %s -- %s' % (logdir, sample_freq, perf_options, command)
        print_info( profile_command)
        subprocess.call(profile_command.split())
        print_info("Epilog of Recording...")
        if p_tcpdump != None:
            p_tcpdump.terminate()
            print_info("tried terminating tcpdump")
        if p_vmstat != None:
            p_vmstat.terminate()
            print_info("tried terminating vmstat")
        if p_mpstat != None:
            p_mpstat.terminate()
            print_info("tried terminating mpstat")
        if p_nvtopo != None:
            p_nvtopo.terminate()
            print_info("tried terminating nvidia-smi topo")
        if p_nvsmi != None:
            p_nvsmi.terminate()
            print_info("tried terminating nvidia-smi dmon")
        #os.system('pkill tcpdump')
        #os.system('pkill mpstat')
        #os.system('pkill vmstat')
        #os.system('pkill nvidia-smi')
    except BaseException:
        print("Unexpected error:", sys.exc_info()[0])
        if p_tcpdump != None:
            p_tcpdump.kill()
            print_info("tried killing tcpdump")
        if p_vmstat != None:
            p_vmstat.kill()
            print_info("tried killing vmstat")
        if p_mpstat != None:
            p_mpstat.kill()
            print_info("tried killing mpstat")
        if p_nvtopo != None:
            p_nvtopo.kill()
            print_info("tried killing nvidia-smi topo")
        if p_nvsmi != None:
            p_nvsmi.kill()
            print_info("tried killing nvidia-smi dmon")
        raise
    print_info("End of Recording")
