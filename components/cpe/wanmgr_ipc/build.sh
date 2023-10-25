#!/bin/sh

# apt install nanomsg-utils libnanomsg-dev
#
gcc wanmgr_ipc.c -o wanmgr_ipc -lnanomsg -lpthread
