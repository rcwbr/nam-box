System
GET /system/info
Returns hardware and OS information.

Response

{\
"hwname": "...", "architecture": "...", "cpu": "...", "platform": "...",\
"bin_compat": "...", "model": "...", "sysdate": "...",\
"python": { "version": "..." },\
"uname": { "machine": "...", "release": "...", "sysname": "...", "version": "..." }\
}
webserver.py:372-402

GET /system/prefs
Returns system preference flags read from /data/ files.

Response

{\
"bluetooth_name": "...",\
"jack_buffer_size": 128,\
"jack_mono_copy": false,\
"jack_sync_mode": false,\
"separate_spdif_outs": false,\
"service_mod_peakmeter": true,\
"service_mod_sdk": false,\
"service_netmanager": false,\
"autorestart_hmi": false\
}
webserver.py:404-463

POST /system/exechange
Execute a system-level change. Dispatches on the type query/form argument.

type=command — cmd argument: reboot, restore, backup-export, backup-import

backup-export / backup-import also require cmd to be "backup-export,\<include_data>,\<include_plugins>" (comma-separated flags 0/1)
Returns true or { "ok": bool, "error": "..." }
type=filecreate — path (one of autorestart-hmi, jack-mono-copy, jack-sync-mode, separate-spdif-outs), create (0/1)

type=filewrite — path (one of bluetooth/name, jack-buffer-size), content

type=service — name (one of hmi-update, mod-peakmeter, mod-sdk, netmanager), enable (0/1), inverted (0/1), persistent (0/1)

Response: true on success, false on invalid input. webserver.py:465-609

POST /system/cleanup
Delete selected data categories. All arguments are 0/1 form fields.

Arguments: banks, favorites, hmiSettings, licenseKeys, pedalboards, plugins

Response

{ "ok": true, "error": "" }
webserver.py:616-671

Updates
POST /update/download/
Upload a MOD OS update image (raw binary body, streamed). Stores to /tmp/os-update/.

Response: { "ok": true, "result": true } webserver.py:673-701

POST /update/begin
Begin the OS update (requires a previously uploaded image). Triggers restore sequence.

Response: true or false webserver.py:689-701

Control Chain Firmware
POST /controlchain/download/
Upload a Control Chain firmware file (raw binary body). Stores to /tmp/cc-update/.

Response: { "ok": true, "result": true } webserver.py:703-716

POST /controlchain/cancel/
Cancel a pending Control Chain firmware update (deletes the uploaded file).

Response: true or false webserver.py:718-725

Plugin Installation
POST /effect/install/
Install a plugin bundle from a .tar.gz archive (raw binary body).

Response

{\
"ok": true,\
"installed": \["http://example.com/plugin"\],\
"removed": \[\]\
}
webserver.py:727-737

POST /sdk/install/
Install a plugin from the MOD SDK. Expects a multipart form with a package field containing a base64-encoded .tar.gz. Sets CORS headers for SDK origins.

Response: Same shape as /effect/install/. webserver.py:762-789

POST /sdk/update
Refresh a single plugin bundle in-place (SDK use). Form arguments: bundle (path), uri.

Response: { "ok": true } or { "ok": false, "error": "..." } webserver.py:791-823

POST /package/uninstall
Uninstall one or more plugin bundles. Body is a JSON array of absolute bundle paths.

Response

{ "ok": true, "removed": \["http://example.com/plugin"\] }
or

{ "ok": false, "error": "...", "removed": \[\] }
webserver.py:1260-1312

Plugin Metadata
GET /effect/list
Return metadata for all installed plugins (mini format).

Response: JSON array of plugin info objects. webserver.py:757-760

GET /effect/get?uri=<uri>
Return full cached plugin info for a single URI. Response is cached with long Cache-Control headers.

Response: Plugin info object, or HTTP 404. webserver.py:963-973

GET /effect/get_non_cached?uri=<uri>
Return non-cached plugin info (reads from disk each time).

Response: Plugin info object, or HTTP 404. webserver.py:975-985

POST /effect/bulk/
Return plugin info for multiple URIs in one request. Body must be a JSON array of URI strings with Content-Type: application/json.

Request body: \["http://example.com/plugin1", "http://example.com/plugin2"\]

Response: { "<uri>": { ...plugin info... }, ... } — URIs that fail are silently omitted. webserver.py:739-755

Plugin Resources
GET /resources/<path>?uri=<uri>
Serve a file from a plugin's resources directory. Falls back to shared resources if not found. webserver.py:825-859

GET /effect/image/(screenshot|thumbnail).png?uri=<uri>
Serve the plugin's screenshot or thumbnail image. Falls back to the default icon image. webserver.py:861-891

GET /effect/file/<prop>?uri=<uri>\[&filename=<name>\]
Serve a plugin GUI file. prop is one of: iconTemplate, settingsTemplate, stylesheet, javascript, custom (requires filename argument for .wasm etc.). webserver.py:893-932

Plugin Instances
GET /effect/add/<instance>?uri=<uri>\[&x=<float>&y=<float>\]
Add a plugin instance to the current pedalboard. instance is a path like /effect/0.

Response: Full plugin info object on success, false on failure. webserver.py:934-954

GET /effect/remove/<instance>
Remove a plugin instance from the current pedalboard.

Response: true or false webserver.py:956-961

Plugin Parameters
POST /effect/parameter/address/<port>
Address a plugin parameter to a hardware actuator. Body is JSON.

Request body

{\
"uri": "http://...",\
"label": "Gain",\
"minimum": 0.0,\
"maximum": 1.0,\
"value": 0.5,\
"steps": 33,\
"tempo": false,\
"dividers": null,\
"page": null,\
"subpage": null,\
"coloured": null,\
"momentary": null,\
"operationalMode": null\
}
Response: true or false webserver.py:1001-1033

POST /effect/parameter/set/
Set a parameter value via the HMI path. Body is a plain string in the format <symbol>/<instance>/<portsymbol>/<value>.

Response: true or false webserver.py:1063-1078

Plugin Presets
GET /effect/preset/load/<instance>?uri=\<preset_uri>
Load a preset for a plugin instance.

Response: true or false webserver.py:1035-1061

GET /effect/preset/save_new/<instance>?name=<name>
Save the current parameter state as a new preset.

Response: Preset URI string or false. webserver.py:1080-1090

GET /effect/preset/save_replace/<instance>?uri=<uri>&bundle=<bundle>&name=<name>
Replace an existing preset with the current parameter state.

Response: true or false webserver.py:1092-1104

GET /effect/preset/delete/<instance>?uri=<uri>&bundle=<bundle>
Delete a preset.

Response: true or false webserver.py:1106-1117

Connections
GET /effect/connect/\<port_from>,\<port_to>
Connect two JACK ports. Port paths use / separators (e.g. /effect/0/out,/effect/1/in).

Response: true or false webserver.py:987-992

GET /effect/disconnect/\<port_from>,\<port_to>
Disconnect two JACK ports.

Response: true or false webserver.py:994-999

Pedalboards
GET /pedalboard/list
List all pedalboards (user + factory). The default pedalboard is always titled "Default".

Response: JSON array of pedalboard info objects. webserver.py:1314-1322

POST /pedalboard/save?title=<title>&asNew=\<0|1>
Save the current pedalboard state.

Response

{ "ok": true, "bundlepath": "/path/to/bundle", "title": "My Pedalboard" }
webserver.py:1324-1343

GET /pedalboard/pack_bundle/?bundlepath=<path>
Download a pedalboard as a .tar.gz archive (includes audio recording if one is active). Returns raw binary. webserver.py:1345-1410

POST /pedalboard/load_bundle/?bundlepath=<path>\[&isDefault=\<0|1>\]
Load a pedalboard from a local bundle path.

Response: { "ok": true, "name": "My Pedalboard" } webserver.py:1412-1434

POST /pedalboard/load_remote/\<pedalboard_id>
Trigger loading a remote pedalboard by ID via the active WebSocket. CORS-restricted to mod.audio / moddevices.com.

Response: true or false webserver.py:1436-1446

POST /pedalboard/load_web/
Upload and immediately load a pedalboard bundle (raw .tar.gz body).

Response: { "ok": true, "result": null } webserver.py:1448-1474

GET /pedalboard/factorycopy/?bundlepath=<path>&title=<title>
Copy a factory pedalboard into the user pedalboards directory with a unique name.

Response: Pedalboard info object with bundlepath and title fields added, or false. webserver.py:1476-1503

GET /pedalboard/info/?bundlepath=<path>
Return full info for a pedalboard bundle.

Response: Pedalboard info object. webserver.py:1505-1508

GET /pedalboard/remove/?bundlepath=<path>
Delete a user pedalboard and remove it from all banks.

Response: true or false webserver.py:1510-1521

GET /pedalboard/image/(screenshot|thumbnail).png?bundlepath=<path>
Serve the pedalboard screenshot or thumbnail PNG. webserver.py:1523-1529

GET /pedalboard/image/generate?bundlepath=<path>
Schedule screenshot generation for a pedalboard.

Response: { "ok": true, "ctime": "1234567890.0" } webserver.py:1531-1540

GET /pedalboard/image/check?bundlepath=<path>
Check whether a screenshot is up to date (cached response).

Response: { "status": <int>, "ctime": "..." } webserver.py:1542-1549

GET /pedalboard/image/wait?bundlepath=<path>
Block until any pending screenshot job for the bundle completes.

Response: { "ok": true, "ctime": "..." } webserver.py:1551-1560

POST /pedalboard/cv_addressing_plugin_port/add?uri=<uri>&name=<name>
Register a CV addressing plugin port.

Response: { "ok": true, "operational_mode": <value> } webserver.py:1562-1572

POST /pedalboard/cv_addressing_plugin_port/remove?uri=<uri>
Unregister a CV addressing plugin port.

Response: true or false webserver.py:1574-1580

POST /pedalboard/transport/set_sync_mode/<mode>
Set the transport sync mode. mode is one of /none, /midi_clock_slave, /link.

Response: true or false webserver.py:1582-1597

Snapshots
POST /snapshot/save
Save the current snapshot in-place.

Response: true or false webserver.py:1599-1603

GET /snapshot/saveas?title=<title>
Save the current state as a new named snapshot.

Response: { "ok": true, "id": <int>, "title": "..." } webserver.py:1605-1620

GET /snapshot/rename?id=<int>&title=<title>
Rename a snapshot.

Response: { "ok": true, "title": "..." } webserver.py:1622-1639

GET /snapshot/remove?id=<int>
Delete a snapshot by index.

Response: true or false webserver.py:1641-1646

GET /snapshot/list
List all snapshots for the current pedalboard.

Response: { "0": "Snapshot A", "1": "Snapshot B", ... } (sparse object, null slots omitted) webserver.py:1648-1652

GET /snapshot/name?id=<int>
Get the name of a single snapshot.

Response: { "ok": true, "name": "Snapshot A" } webserver.py:1654-1661

GET /snapshot/load?id=<int>
Load a snapshot by index.

Response: true or false webserver.py:1663-1670

Banks
GET /banks/
List all banks with full pedalboard metadata embedded. Broken pedalboards are excluded.

Response: JSON array of bank objects, each containing a pedalboards array of full pedalboard info. webserver.py:1679-1707

POST /banks/save/
Save the full banks list. Body is a JSON array of bank objects.

Response: true webserver.py:1709-1713

Authentication
POST /auth/nonce/
Create a signed token message. Body is JSON with a nonce field.

Response: Token message object (empty {} if token module unavailable). webserver.py:2063-2071

POST /auth/token/
Decode and decrypt an access token. Body is the raw encrypted token string.

Response: { "access_token": "..." } webserver.py:2073-2077

Recording
GET /recording/start
Start audio recording.

Response: true webserver.py:2079-2082

GET /recording/stop
Stop audio recording.

Response: true webserver.py:2084-2087

GET /recording/play/start
Start playback of the current recording.

Response: true

GET /recording/play/wait
Long-poll: holds the connection open until playback finishes, then responds.

Response: true

GET /recording/play/stop
Stop playback.

Response: true webserver.py:2094-2122

GET /recording/download
Download the current recording as a base64-encoded audio blob.

Response: { "ok": true, "audio": "<base64>" } or { "ok": false, "audio": "" } webserver.py:2124-2131

GET /recording/reset
Delete the current recording.

Response: true webserver.py:2089-2092

Tokens (Cloud)
GET /tokens/get
Read stored cloud tokens from disk.

Response: { "ok": true, "user_id": "...", "access_token": "...", "refresh_token": "..." } or { "ok": false } webserver.py:2143-2157

POST /tokens/save/
Save cloud tokens to disk. Body is a JSON object (the expires_in_days key is stripped before saving).

Response: true webserver.py:2159-2170

GET /tokens/delete
Delete stored cloud tokens.

Response: true webserver.py:2133-2141

Files
GET /files/list/?types=\<type1,type2,...>
List user files of the given type(s). Supported types: audioloop, audiorecording, audiosample, audiotrack, cabsim, h2drumkit, ir, midiclip, midisong, sf2, sfz, aidadspmodel, nammodel.

Response

{\
"ok": true,\
"files": \[\
{ "fullname": "/path/to/file.wav", "basename": "file.wav", "filetype": "audiosample" }\
\]\
}
webserver.py:2172-2261

JACK / MIDI
GET /jack/get_midi_devices
Get the current MIDI device configuration.

Response

{\
"devsInUse": \[...\],\
"devList": \[...\],\
"names": {...},\
"midiAggregatedMode": false\
}
webserver.py:2006-2014

POST /jack/set_midi_devices
Set MIDI device configuration. Body is JSON.

Request body: { "devs": \[...\], "midiAggregatedMode": false, "midiLoopback": false }

Response: true webserver.py:2016-2025

Favorites
POST /favorites/add?uri=<uri>
Add a plugin URI to the favorites list.

Response: true or false (if already present) webserver.py:2027-2043

POST /favorites/remove?uri=<uri>
Remove a plugin URI from the favorites list.

Response: true or false (if not present) webserver.py:2045-2061

Configuration
POST /config/set?key=<key>&value=<value>
Persist a single UI preference key/value pair.

Response: true webserver.py:1987-1993

POST /save_user_id/?name=<name>&email=<email>
Save the user's display name and email.

Response: true webserver.py:1995-2004

Miscellaneous
GET /ping/
Ping the HMI and measure round-trip time.

Response: { "ihm_online": true, "ihm_time": 3 } (time in ms) or { "ihm_online": false, "ihm_time": 0 } webserver.py:1905-1929

GET /hello/
Check whether the UI is online and get the firmware version. CORS-enabled for mod.audio / moddevices.com.

Response: { "online": true, "version": "v1.2.3" } webserver.py:1931-1937

GET /truebypass/(Left|Right)/(true|false)
Set hardware true-bypass state for the left or right channel.

Response: true or false webserver.py:1939-1942

POST /set_buffersize/(128|256)
Set the JACK audio buffer size. On real hardware, also persists the setting to /data/jack-buffer-size.

Response: { "ok": true, "size": 128 } webserver.py:1944-1959

POST /reset_xruns/
Reset the JACK xrun counter.

Response: true webserver.py:1961-1964

POST /switch_cpu_freq/
Cycle to the next available CPU frequency step.

Response: true or false webserver.py:1966-1985

GET /reset/
Reset the dashboard — unloads all plugins and clears the current pedalboard state.

Response: true or false webserver.py:1672-1677
