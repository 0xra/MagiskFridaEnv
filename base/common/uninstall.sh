#!/system/bin/sh
# Do NOT assume where your module will be located.
# ALWAYS use $MODDIR if you need to know where this script
# and module is placed.
# This will make sure your module will still work
# if Magisk change its mount point in the future
MODDIR=${0%/*}

# This script will be executed in uninstall mode
SDCARD_STORAGE="/storage/emulated/0/mfe-frida-server"
if [ -d ${SDCARD_STORAGE} ]; then
    rm -rf ${SDCARD_STORAGE}
fi 