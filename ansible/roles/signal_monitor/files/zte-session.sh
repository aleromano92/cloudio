# Managed by Ansible (signal_monitor role). Sourced, never executed.
#
# One authenticated session against the ZTE MC801A's goform API, shared by the
# sampler and the band scheduler. Functions take the router IP and a cookie jar
# so nothing here depends on the caller's globals.
#
# Command shapes (login hashing, AD token, band masks) were read off the
# router's own JS and the Miononno bookmarklet, not guessed.

ZTE_TLS_CONF=/etc/cloudio-signal-monitor/openssl-legacy.cnf
ZTE_UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

_zte_hdrs() {
  printf '%s\n' \
    -H "Accept: application/json, text/javascript, */*; q=0.01" \
    -H "Referer: https://$1/" \
    -H "X-Requested-With: XMLHttpRequest" \
    -H "User-Agent: ${ZTE_UA}"
}

_zte_md5() { printf '%s' "$1" | md5sum | cut -d' ' -f1; }

# zte_login <router_ip> <password> <jar> -> 0 on success
zte_login() {
  local ip=$1 password=$2 jar=$3
  local -a hdrs; mapfile -t hdrs < <(_zte_hdrs "$ip")
  [ -n "$password" ] || return 1

  local ld hash1 hash2 login
  ld=$(OPENSSL_CONF="$ZTE_TLS_CONF" curl -sk --connect-timeout 8 --max-time 15 "${hdrs[@]}" -b 'stok=""' \
    "https://${ip}/goform/goform_get_cmd_process?isTest=false&cmd=LD&_=$(date +%s%3N)" \
    | jq -r '.LD // empty' 2>/dev/null)
  [ -n "$ld" ] || return 1

  hash1=$(printf '%s' "$password" | sha256sum | cut -d' ' -f1 | tr 'a-f' 'A-F')
  hash2=$(printf '%s' "${hash1}${ld}" | sha256sum | cut -d' ' -f1 | tr 'a-f' 'A-F')
  login=$(OPENSSL_CONF="$ZTE_TLS_CONF" curl -sk -c "$jar" -X POST "https://${ip}/goform/goform_set_cmd_process" \
    "${hdrs[@]}" -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" -b 'stok=""' \
    --connect-timeout 8 --max-time 15 --data "isTest=false&goformId=LOGIN&password=${hash2}")
  printf '%s' "$login" | jq -e '.result == "0"' >/dev/null 2>&1
}

# zte_get <router_ip> <jar> <comma,separated,cmds> -> JSON on stdout
zte_get() {
  local ip=$1 jar=$2 cmds=$3
  local -a hdrs; mapfile -t hdrs < <(_zte_hdrs "$ip")
  OPENSSL_CONF="$ZTE_TLS_CONF" curl -sk -b "$jar" "${hdrs[@]}" --connect-timeout 8 --max-time 15 \
    "https://${ip}/goform/goform_get_cmd_process?multi_data=1&cmd=${cmds}"
}

# Readings come back as strings, with "" for "not measured" and -32768 for the
# modem's own "no value" sentinel; both become null so they can't be averaged
# or compared as if they were 0.
ZTE_NORMALISE='with_entries(.value |= (if . == "" then null
  elif (type == "string" and test("^-?[0-9]+(\\.[0-9]+)?$")) then tonumber
  else . end))
| map_values(if (type == "number" and (. == -32768 or . == -3276.8)) then null else . end)'

# zte_status <router_ip> <jar> <comma,separated,cmds> -> normalised JSON ({} on failure)
# jq exits 0 and prints nothing when its input is empty, so a failed request
# would otherwise pass an empty string off as a reading.
zte_status() {
  local out
  out=$(zte_get "$1" "$2" "$3" | jq -ce "$ZTE_NORMALISE" 2>/dev/null)
  [ -n "$out" ] || out='{}'
  printf '%s' "$out"
}

# Same, but retries until the readings are actually there. Two different things
# produce a blank answer, and both are transient:
#   - the modem is re-registering after a band change;
#   - the router allows one logged-in session at a time, so opening its web UI
#     in a browser silently evicts this one -- and an evicted session gets empty
#     strings back, not an auth error. Hence the re-login between attempts.
# Without this a blank reading would be scored as "this band has no coverage".
# Needs ZTE_PASSWORD in the environment to re-login.
# zte_status_wait <router_ip> <jar> <cmds> <tries> <delay>
zte_status_wait() {
  local ip=$1 jar=$2 cmds=$3 tries=$4 delay=$5 out i
  for ((i = 0; i < tries; i++)); do
    out=$(zte_status "$ip" "$jar" "$cmds")
    printf '%s' "$out" | jq -e '.lte_rsrp != null' >/dev/null 2>&1 && { printf '%s' "$out"; return 0; }
    sleep "$delay"
    zte_login "$ip" "${ZTE_PASSWORD:-}" "$jar" >/dev/null 2>&1
  done
  [ -n "$out" ] || out='{}'
  printf '%s' "$out"
}

# Every set command is signed with AD = md5(md5(wa_inner_version + cr_version) + RD),
# read fresh each time because RD is a nonce.
zte_ad() {
  local ip=$1 jar=$2 v
  v=$(zte_get "$ip" "$jar" "wa_inner_version,cr_version,RD")
  local inner cr rd
  inner=$(printf '%s' "$v" | jq -r '.wa_inner_version // empty')
  cr=$(printf '%s' "$v" | jq -r '.cr_version // empty')
  rd=$(printf '%s' "$v" | jq -r '.RD // empty')
  [ -n "$rd" ] || return 1
  _zte_md5 "$(_zte_md5 "${inner}${cr}")${rd}"
}

# zte_set <router_ip> <jar> <urlencoded body without isTest/AD> -> response on stdout
#
# An evicted session (see zte_status_wait) can't produce an AD token and gets
# the command rejected, so one re-login is attempted before giving up.
zte_set() {
  local ip=$1 jar=$2 body=$3 ad out attempt
  local -a hdrs; mapfile -t hdrs < <(_zte_hdrs "$ip")
  for attempt in 1 2; do
    if ad=$(zte_ad "$ip" "$jar") && [ -n "$ad" ]; then
      out=$(OPENSSL_CONF="$ZTE_TLS_CONF" curl -sk -b "$jar" -X POST "https://${ip}/goform/goform_set_cmd_process" \
        "${hdrs[@]}" -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
        --connect-timeout 8 --max-time 20 --data "isTest=false&${body}&AD=${ad}")
      if printf '%s' "$out" | jq -e '.result == "success"' >/dev/null 2>&1; then
        printf '%s' "$out"
        return 0
      fi
    fi
    [ "$attempt" = 1 ] && zte_login "$ip" "${ZTE_PASSWORD:-}" "$jar" >/dev/null 2>&1
  done
  [ -n "$out" ] || out='{}'
  printf '%s' "$out"
  return 1
}

# LTE bands are a bitmask: band N is bit N-1. AUTO is the firmware's own
# "every supported band" constant, straight from the bookmarklet.
ZTE_LTE_BAND_AUTO=0xA3E2AB0908DF
zte_lte_mask() {
  local mask=0 band
  for band in "$@"; do mask=$(( mask | (1 << (band - 1)) )); done
  printf '0x%x' "$mask"
}

# zte_set_lte_bands <router_ip> <jar> <AUTO|band...>
zte_set_lte_bands() {
  local ip=$1 jar=$2; shift 2
  local mask
  if [ "$1" = "AUTO" ]; then mask=$ZTE_LTE_BAND_AUTO; else mask=$(zte_lte_mask "$@"); fi
  zte_set "$ip" "$jar" "goformId=BAND_SELECT&is_gw_band=0&gw_band_mask=0&is_lte_band=1&lte_band_mask=${mask}"
}

# NR bands are a comma-separated list, not a mask.
ZTE_NR_BAND_AUTO="1,2,3,5,7,8,20,28,38,41,50,51,66,70,71,74,75,76,77,78,79,80,81,82,83,84"
zte_set_nr_bands() {
  local ip=$1 jar=$2 bands=$3
  [ "$bands" = "AUTO" ] && bands=$ZTE_NR_BAND_AUTO
  zte_set "$ip" "$jar" "goformId=WAN_PERFORM_NR5G_BAND_LOCK&nr5g_band_mask=${bands}"
}

zte_reboot() { zte_set "$1" "$2" "goformId=REBOOT_DEVICE"; }

# EARFCN -> LTE band, for the bands this operator actually uses here. Used to
# read the neighbour list, which reports EARFCNs rather than band numbers.
zte_earfcn_band() {
  local e=$1
  if   [ "$e" -le 599 ];                          then echo 1
  elif [ "$e" -ge 1200 ] && [ "$e" -le 1949 ];    then echo 3
  elif [ "$e" -ge 2750 ] && [ "$e" -le 3449 ];    then echo 7
  elif [ "$e" -ge 6150 ] && [ "$e" -le 6449 ];    then echo 20
  elif [ "$e" -ge 9210 ] && [ "$e" -le 9659 ];    then echo 28
  elif [ "$e" -ge 37750 ] && [ "$e" -le 38249 ];  then echo 38
  elif [ "$e" -ge 38650 ] && [ "$e" -le 39649 ];  then echo 40
  else echo 0; fi
}
