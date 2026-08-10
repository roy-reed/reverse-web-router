const NATIVE_HOST = "com.roy.reverse_web_router";

async function getBinding() {
  return chrome.storage.local.get(["boundProjectName", "boundProjectFingerprint", "lastStatus"]);
}

chrome.runtime.onMessage.addListener((message, _sender, respond) => {
  if (message?.type !== "handoff-candidate") return;
  (async () => {
    const binding = await getBinding();
    const fingerprint = message.project?.projectFingerprint;
    if (!fingerprint || fingerprint !== binding.boundProjectFingerprint) {
      const status = {ok: false, error: "Rejected: handoff is outside the bound ChatGPT Project"};
      await chrome.storage.local.set({lastStatus: status});
      respond(status);
      return;
    }
    chrome.runtime.sendNativeMessage(
      NATIVE_HOST,
      {project_fingerprint: fingerprint, packet: message.packet},
      async (reply) => {
        const status = chrome.runtime.lastError
          ? {ok: false, error: chrome.runtime.lastError.message}
          : reply;
        await chrome.storage.local.set({lastStatus: status});
        respond(status);
      }
    );
  })();
  return true;
});
