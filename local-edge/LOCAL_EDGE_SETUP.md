# LOCAL_EDGE setup boundary

`LOCAL_EDGE` is optional. It is needed only for local files, desktop applications, hardware, local credentials, proprietary environments, or local final acceptance.

This repository does not install the extension or register the Native Messaging host automatically. Before installation:

1. Copy `bridge/config.example.json` to a local configuration path outside the repository.
2. Replace the project fingerprint and workspace aliases locally. Do not place real absolute paths in GitHub, ChatGPT, Issues, logs, or web-returnable receipts.
3. Load `extension/` as an unpacked Manifest V3 extension.
4. Replace the extension ID and local launcher path in `bridge/native-messaging-host.json.template`, then register it using the documented Chrome or Edge Native Messaging registry location.
5. Open the intended ChatGPT Project and click `绑定当前项目` in the extension popup.
6. Run a dry-run packet first. The supplied host only validates, translates, selects a backend, and returns a dry-run receipt; it does not expose a TCP listener or execute arbitrary shell text.

To disable, unbind the Project, disable/remove the unpacked extension, and remove the Native Messaging registration. Removing these components does not affect GitHub-cloud execution.
