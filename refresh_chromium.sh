#!/bin/bash
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
pkill chromium 2>/dev/null
sleep 3
/usr/lib/chromium/chromium \
  --ozone-platform=wayland \
  --kiosk --noerrdialogs --disable-infobars --no-first-run \
  --disable-gpu --disable-dev-shm-usage --disable-features=Translate \
  file:///home/lif/infoskaerm/index.html > /dev/null 2>&1 &
