#!/bin/bash
# NCS v3.3.0 build environment for the reSpeaker clone tree.
# Source it in git-bash:  source ./nrf_env.sh
# Then build:             west build --build-dir build-clip --pristine --board clip/nrf5340/cpuapp applications/clip
#
# SDK root:  C:\ncs\v3.3.0   (toolchain bundle 936afb6332 per toolchains.json)
# NOTE: NCS v3.4.2 does NOT build this tree (board partitioning API drift,
# s0_partition vs slot0_partition) — always use v3.3.0 here.

TC="/c/ncs/toolchains/936afb6332"

export PATH="$TC/mingw64/bin:$TC/bin:$TC/opt/bin:$TC/opt/bin/Scripts:$TC/opt/zephyr-sdk/arm-zephyr-eabi/bin:$PATH"
export PYTHONPATH="$TC/opt/bin:$TC/opt/bin/Lib:$TC/opt/bin/Lib/site-packages"

export ZEPHYR_TOOLCHAIN_VARIANT=zephyr
export ZEPHYR_SDK_INSTALL_DIR="C:/ncs/toolchains/936afb6332/opt/zephyr-sdk"
export ZEPHYR_BASE="C:/ncs/v3.3.0/zephyr"
export ZEPHYR_EXTRA_MODULES="C:/Users/Home/Documents/ai/neo_n1_clone/try1/reSpeaker_Clip-main/reSpeaker_Clip-main"

echo "west:  $(west --version 2>/dev/null || echo 'not on PATH')"
echo "sdk:   $ZEPHYR_BASE"
