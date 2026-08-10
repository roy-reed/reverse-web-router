async function activeProject() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id || !tab.url?.startsWith("https://chatgpt.com/")) throw new Error("当前标签不是 ChatGPT");
  return chrome.tabs.sendMessage(tab.id, {type: "inspect-project"});
}

async function render() {
  const data = await chrome.storage.local.get(["boundProjectName", "boundProjectFingerprint", "lastStatus"]);
  document.querySelector("#binding").textContent = data.boundProjectFingerprint
    ? `已绑定：${data.boundProjectName || data.boundProjectFingerprint}`
    : "未绑定项目";
  document.querySelector("#status").textContent = JSON.stringify(data.lastStatus || {}, null, 2);
}

document.querySelector("#bind").addEventListener("click", async () => {
  try {
    const project = await activeProject();
    if (!project?.projectFingerprint || !project?.projectName) throw new Error("无法确认当前项目归属");
    await chrome.storage.local.set({
      boundProjectName: project.projectName,
      boundProjectFingerprint: project.projectFingerprint,
      lastStatus: {ok: true, message: "Project bound; no local task executed."}
    });
  } catch (error) {
    await chrome.storage.local.set({lastStatus: {ok: false, error: String(error)}});
  }
  render();
});

document.querySelector("#unbind").addEventListener("click", async () => {
  await chrome.storage.local.remove(["boundProjectName", "boundProjectFingerprint"]);
  await chrome.storage.local.set({lastStatus: {ok: true, message: "Project unbound."}});
  render();
});

render();
