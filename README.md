# Lystrup IF — Infoskærm

Infoskærmen er en Raspberry Pi der kører en hjemmeside i fuld skærm (kiosk-tilstand via Chromium). Siden vises automatisk fra kl. 07 til 22.

## Hvad der vises

- **Venstre panel:** Kampprogram — hold, tidspunkt, bane og omklædning
- **Højre panel:** Baneplan (tegning af banerne)
- **Header:** Dato, ur og vejr (temperatur, vind, vindretning)
- **Bundlinje:** Sponsorlogoer

---

## Filer

| Fil | Funktion |
|---|---|
| `index.html` | Selve skærmen — alt HTML/CSS/JS |
| `dbu_proxy.py` | Python-server der henter kampe fra DBU (port 8765, cacher 10 min) |
| `refresh_chromium.sh` | Genstarter Chromium med de rigtige Wayland-flag |
| `matches.json` | Manuel kampdata til kampe der ikke er i DBU endnu |

Al kode ligger på GitHub: `github.com/LystrupIFFodbold/infoskaerm`  
På Pi'en bor filerne i: `/home/lif/infoskaerm/`

---

## Adgang til Pi'en

**Grafisk (anbefalet):** `connect.raspberrypi.com` → log ind → Screen sharing

**SSH:**
```
ssh lif@<Pi'ens IP>
```

---

## Hvordan kampdata fungerer

Skærmen kombinerer data fra to kilder:

1. **`matches.json`** — manuelle kampe du selv har tilføjet (bruges primært de næste 3 dage)
2. **DBU Klub Office** (klubid 587) — hentes automatisk via den lokale Python-proxy på port 8765

Kampe sorteres kronologisk og bladres automatisk 5 ad gangen (skifter hvert 9. sekund). Næste kamp markeres med en rød badge.

---

## Automatik (cron-jobs på Pi'en)

Vis cron-listen med: `crontab -l`

| Tidspunkt | Hvad sker der |
|---|---|
| Hvert 5. min | `git pull` fra GitHub — ny commit → Chromium genstartes automatisk |
| Kl. 07:00 | Skærm tændes (`wlopm --on HDMI-A-2`) |
| Kl. 22:00 | Skærm slukkes (`wlopm --off HDMI-A-2`) |
| Opstart | `dbu_proxy.py` startes automatisk |

---

## Opdatér kampe manuelt

Åbn `matches.json` på GitHub og tilføj en post:

```json
{
  "date": "DD-MM-ÅÅÅÅ",
  "time": "HH:MM",
  "aargang": "U15 / Herrer Serie 4 / osv.",
  "homeTeam": "Lystrup IF",
  "awayTeam": "Modstander IF",
  "omklædnHjem": "Omklædning 1",
  "omklædnUde": "Omklædning 2",
  "omklædnDommer": "Omklædning 6",
  "bane": "Kunstgræs"
}
```

Commit på GitHub → Pi'en henter det automatisk inden for 5 minutter.

---

## Tilføj eller fjern sponsorer

Find `const sponsors = [...]` i `index.html` og tilføj/fjern en linje:

```javascript
{ name: 'Sponsor Navn', logo: 'https://587-lystrup-if.euwest01.umbraco.io/media/1234/logo.png' }
```

Logoer uploades i **Umbraco CMS**: `587-lystrup-if.euwest01.umbraco.io`  
Herefter commit på GitHub → opdateres på skærmen inden for 5 minutter.

---

## Manuel genstart af Chromium

Hvis skærmen viser desktop i stedet for infoskærmen:

```bash
bash /home/lif/infoskaerm/refresh_chromium.sh
```

Scriptet dræber Chromium, venter 3 sekunder og starter det igen med de rigtige Wayland-flag.

---

## Fejlfinding

### Ingen kampe vises

Tjek om DBU-proxyen kører:
```bash
curl -s http://localhost:8765 | wc -c   # Skal returnere > 1000
```

Hvis fejl — genstart proxyen:
```bash
pkill -f dbu_proxy.py
nohup python3 /home/lif/infoskaerm/dbu_proxy.py >> /home/lif/infoskaerm/dbu_proxy.log 2>&1 &
```

### Pi henter ikke opdateringer fra GitHub

```bash
crontab -l                        # Tjek at cron-jobs er der
cd ~/infoskaerm && git pull       # Test manuelt
ping -c 3 github.com              # Tjek internet
```

### Skærm tænder/slukker ikke automatisk

```bash
crontab -l | grep wlopm
# Test manuelt:
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 wlopm --on HDMI-A-2
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 wlopm --off HDMI-A-2
```

### Chromium crasher efter start

```bash
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 /usr/lib/chromium/chromium \
  --ozone-platform=wayland --disable-gpu --kiosk --no-first-run \
  --disable-dev-shm-usage file:///home/lif/infoskaerm/index.html \
  2>/tmp/cr_debug.log &
sleep 10 && cat /tmp/cr_debug.log
```

---

## Vigtige adresser

| System | Adresse |
|---|---|
| GitHub-kode | `github.com/LystrupIFFodbold/infoskaerm` |
| Pi fjernbetjening | `connect.raspberrypi.com` |
| Umbraco CMS (logoer) | `587-lystrup-if.euwest01.umbraco.io` |
| DBU Klub Office | `kluboffice.dbu.dk` |
| Filer på Pi | `/home/lif/infoskaerm/` |
| Pi brugernavn (SSH) | `lif` |
