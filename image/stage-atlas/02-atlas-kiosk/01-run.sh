#!/bin/bash -e
# Step 02-B: Write .bash_profile (auto-starts X on tty1 login)
#            and minimal openbox config (no decorations, fullscreen).

on_chroot << CHROOT
set -e

# .bash_profile — only runs when atlas logs in interactively on tty1.
# SSH sessions (tty != tty1) drop straight to bash, so SSH stays usable.
cat > /home/atlas/.bash_profile << 'PROFILE'
# Atlas OS auto-start
# Launch X + kiosk only on tty1 (the physical display).
# SSH sessions skip this block and get a normal bash prompt.
if [ "$(tty)" = "/dev/tty1" ]; then
    exec startx /home/atlas/AtlasOS/scripts/start-kiosk.sh -- -nocursor \
        >> /home/atlas/AtlasOS/logs/xorg.log 2>&1
fi
PROFILE
chown atlas:atlas /home/atlas/.bash_profile

# .bashrc for SSH sessions — activate the venv automatically
cat > /home/atlas/.bashrc << 'RC'
# Atlas OS .bashrc
source /home/atlas/AtlasOS/.venv/bin/activate
export ATLAS_MODELS_DIR=/home/atlas/AtlasOS/models
export PATH="$PATH:/home/atlas/AtlasOS/.venv/bin"
alias atlas-logs="tail -f /home/atlas/AtlasOS/logs/kiosk.log"
alias atlas-restart="sudo systemctl restart atlas-kiosk"
RC
chown atlas:atlas /home/atlas/.bashrc

# Minimal openbox config: no titlebar, no right-click menu, fullscreen
mkdir -p /home/atlas/.config/openbox
cat > /home/atlas/.config/openbox/rc.xml << 'OPENBOX'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc"
                xmlns:xi="http://www.w3.org/2001/XInclude">
  <resistance><strength>10</strength><screen_edge_strength>20</screen_edge_strength></resistance>
  <focus><focusNew>yes</focusNew><followMouse>no</followMouse><focusDelay>200</focusDelay></focus>
  <placement><policy>Smart</policy></placement>
  <theme><name>Clearlooks</name><titleLayout>NLIMC</titleLayout>
    <keepBorder>yes</keepBorder><animateIconify>yes</animateIconify>
    <font place="ActiveWindow"><name>sans</name><size>8</size><weight>Bold</weight></font>
  </theme>
  <desktops><number>1</number><firstdesk>1</firstdesk><names><name>Atlas OS</name></names></desktops>
  <resize><drawContents>yes</drawContents></resize>
  <keyboard>
    <keybind key="A-F4"><action name="Close"/></keybind>
    <keybind key="A-F2"><action name="Execute"><command>xterm</command></action></keybind>
  </keyboard>
  <mouse><dragThreshold>1</dragThreshold><doubleClickTime>200</doubleClickTime>
    <screenEdgeWarpTime>400</screenEdgeWarpTime><screenEdgeWarpMouse>false</screenEdgeWarpMouse>
  </mouse>
  <applications>
    <application class="*">
      <decor>no</decor>
      <maximized>yes</maximized>
      <layer>normal</layer>
    </application>
  </applications>
</openbox_config>
OPENBOX
chown -R atlas:atlas /home/atlas/.config

echo "==> .bash_profile and openbox config written."
CHROOT
