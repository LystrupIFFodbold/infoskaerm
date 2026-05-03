#!/bin/bash
pkill chromium 2>/dev/null
sleep 3
WAYLAND_DISPLAY=wayland-0 /usr/lib/chromium/chromium \
  --kiosk --noerrdialogs --disable-infobars --no-first-run \
  --use-angle=gles --disable-dev-shm-usage --disable-features=Translate \
  file:///home/lif/infoskaerm/index.html > /dev/null 2>&1 &
