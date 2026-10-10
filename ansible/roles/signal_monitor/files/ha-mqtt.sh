# Shared by the signal monitor and the watchdog: publishing the Router's
# readings to Home Assistant over MQTT (ADR-0012). The node stays the Router's
# only client; HA only ever hears about it from here.
#
# Fire-and-forget on purpose. A broker that's down costs HA a gap, never a
# sample: metrics.jsonl stays the complete record. Nothing here fails its
# caller, and nothing is queued for replay.
#
# The broker address and login live in mosquitto_pub's own options file
# (root-only), so the password never appears on a command line. Without that
# file every publish is a no-op.

HA_MQTT_CONFIG_HOME=/etc/cloudio-signal-monitor/mqtt
HA_ROUTER_DISCOVERY_TOPIC=homeassistant/device/cloudio_router/config
HA_ROUTER_STATE_TOPIC=cloudio/router/state
HA_UPLINK_TOPIC=cloudio/router/uplink
# Two missed hourly samples, then HA shows the Router's readings as
# unavailable instead of the last good value forever.
HA_ROUTER_EXPIRE_SECONDS=7200
# The watchdog's heartbeat is once a minute.
HA_UPLINK_EXPIRE_SECONDS=180

# ha_mqtt_pub TOPIC PAYLOAD. Retained, so HA has the latest value straight
# after its own restart rather than waiting for the next publish.
ha_mqtt_pub() {
  [ -r "$HA_MQTT_CONFIG_HOME/mosquitto_pub" ] || return 0
  XDG_CONFIG_HOME=$HA_MQTT_CONFIG_HOME timeout 10 \
    mosquitto_pub -q 1 -r -t "$1" -m "$2" >/dev/null 2>&1 || true
}

# The configured LTE lock as the dashboard on :8420 shows it: "B1+B3+B20",
# or AUTO for the firmware's all-bands mask. Prints nothing for no reading.
ha_lte_lock_label() {
  local mask=$1 band bands=()
  [[ $mask =~ ^0x[0-9a-fA-F]+$ ]] || return 0
  for band in $(seq 1 64); do
    (( mask & (1 << (band - 1)) )) && bands+=("B$band")
  done
  if [ "${#bands[@]}" -gt 8 ]; then echo AUTO; else (IFS=+; echo "${bands[*]}"); fi
}

# One device-based discovery message for the whole Router: every entity, and
# the device they belong to. Republished with every sample, so a broker that
# lost its retained messages heals itself within the hour.
ha_router_discovery() {
  jq -nc \
    --arg state "$HA_ROUTER_STATE_TOPIC" --arg uplink "$HA_UPLINK_TOPIC" \
    --argjson exp "$HA_ROUTER_EXPIRE_SECONDS" --argjson uexp "$HA_UPLINK_EXPIRE_SECONDS" '
    def sensor($id; $name; $field): {
      p: "sensor", name: $name, uniq_id: "cloudio_router_\($id)", obj_id: "router_5g_\($id)",
      stat_t: $state, val_tpl: "{{ value_json.\($field) }}", exp_aft: $exp
    };
    def measure($id; $name; $field; $unit; $cls; $prec):
      sensor($id; $name; $field) + {unit_of_meas: $unit, stat_cla: "measurement", sug_dsp_prc: $prec}
      + (if $cls then {dev_cla: $cls} else {} end);
    {
      dev: {ids: ["cloudio_router"], name: "Router 5G", mf: "ZTE", mdl: "MC801A", sa: "Casetta Legno"},
      o: {name: "cloudio signal_monitor"},
      cmps: {
        download:     measure("download"; "Download"; "download_mbps"; "Mbit/s"; "data_rate"; 0),
        upload:       measure("upload"; "Upload"; "upload_mbps"; "Mbit/s"; "data_rate"; 0),
        ping:         measure("ping"; "Ping"; "ping_ms"; "ms"; "duration"; 0),
        jitter:       measure("jitter"; "Jitter"; "jitter_ms"; "ms"; "duration"; 0),
        nr_rsrp:      measure("nr_rsrp"; "5G signal strength"; "nr_rsrp"; "dBm"; "signal_strength"; 0),
        nr_sinr:      measure("nr_sinr"; "5G signal quality"; "nr_sinr"; "dB"; null; 1),
        modem_4g_temp: measure("modem_4g_temp"; "4G modem temperature"; "modem_4g_temp"; "°C"; "temperature"; 0),
        modem_5g_temp: measure("modem_5g_temp"; "5G modem temperature"; "modem_5g_temp"; "°C"; "temperature"; 0),
        network_mode: sensor("network_mode"; "Network mode"; "network_mode"),
        mast:         sensor("mast"; "Mast"; "mast"),
        lte_band:     sensor("lte_band"; "4G band"; "lte_band"),
        lte_band_lock: sensor("lte_band_lock"; "4G band lock"; "lte_band_lock"),
        nr_cell:      sensor("nr_cell"; "5G cell"; "nr_cell"),
        wan_ip:       (sensor("wan_ip"; "WAN IP"; "wan_ip") + {ent_cat: "diagnostic"}),
        last_sample:  (sensor("last_sample"; "Last sample"; "timestamp")
                       + {dev_cla: "timestamp", ent_cat: "diagnostic"}),
        uplink: {
          p: "binary_sensor", name: "Internet uplink", uniq_id: "cloudio_router_uplink",
          obj_id: "router_5g_internet_uplink", dev_cla: "connectivity",
          stat_t: $uplink, pl_on: "ON", pl_off: "OFF", exp_aft: $uexp
        }
      }
    }'
}

# ha_router_state SAMPLE -- one metrics.jsonl line, flattened to the fields
# the discovery message reads. A half that failed (login, speedtest) leaves
# its fields null, which HA shows as unknown rather than a fake zero.
ha_router_state() {
  local sample=$1 lock
  lock=$(ha_lte_lock_label "$(printf '%s' "$sample" | jq -r '.zte.lte_band_lock // empty')")
  printf '%s' "$sample" | jq -c --arg lock "$lock" '
    def r1: if . == null then null else (. * 10 | round) / 10 end;
    {
      timestamp,
      download_mbps: (.speedtest.download_mbps | r1),
      upload_mbps:   (.speedtest.upload_mbps | r1),
      ping_ms:       (.speedtest.ping_ms | r1),
      jitter_ms:     (.speedtest.jitter_ms | r1),
      nr_rsrp:       .zte.Z5g_rsrp,
      nr_sinr:       .zte.Z5g_SINR,
      modem_4g_temp: .zte.pm_sensor_mdm,
      modem_5g_temp: .zte.pm_modem_5g,
      network_mode:  .zte.network_type,
      mast:          .zte.enodeb_id,
      lte_band:      (.zte.lte_band | if . == null then null else "B\(.)" end),
      lte_band_lock: (if $lock == "" then null else $lock end),
      nr_cell:       .zte.nr5g_pci,
      wan_ip:        .zte.wan_ipaddr
    }'
}

# ha_publish_sample SAMPLE -- discovery first, so a fresh HA knows the
# entities before their first state arrives.
ha_publish_sample() {
  ha_mqtt_pub "$HA_ROUTER_DISCOVERY_TOPIC" "$(ha_router_discovery)"
  ha_mqtt_pub "$HA_ROUTER_STATE_TOPIC" "$(ha_router_state "$1")"
}
