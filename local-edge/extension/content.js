const seenTaskIds = new Set();

function projectState() {
  const projectLink = document.querySelector('a[href*="/g/g-p-"][href$="/project"]');
  const match = location.pathname.match(/\/g\/(g-p-[^/]+)/);
  return {
    projectName: projectLink?.textContent?.trim() || null,
    projectFingerprint: match?.[1] || null,
    url: location.href
  };
}

function packetCandidates() {
  return [...document.querySelectorAll("pre code")].flatMap((node) => {
    const text = node.textContent?.trim() || "";
    if (!text.startsWith("{") || !text.includes('"protocol"')) return [];
    try {
      const packet = JSON.parse(text);
      return packet.protocol === "rwrouter/1.1" ? [packet] : [];
    } catch {
      return [];
    }
  });
}

function inspect() {
  const project = projectState();
  for (const packet of packetCandidates()) {
    if (!packet.task_id || seenTaskIds.has(packet.task_id)) continue;
    seenTaskIds.add(packet.task_id);
    chrome.runtime.sendMessage({type: "handoff-candidate", packet, project});
  }
}

chrome.runtime.onMessage.addListener((message, _sender, respond) => {
  if (message?.type === "inspect-project") respond(projectState());
});

new MutationObserver(inspect).observe(document.documentElement, {childList: true, subtree: true});
inspect();
