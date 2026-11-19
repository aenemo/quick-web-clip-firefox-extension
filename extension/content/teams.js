// Tidies a copy of a Microsoft Teams chat before it becomes Markdown.
// Injected before extract.js; defines globalThis.__qwcTeams.
(() => {
  const isTeamsHost = (host) =>
    /(^|\.)teams\.(cloud\.)?microsoft(\.com)?$/i.test(host) || /(^|\.)teams\.live\.com$/i.test(host);

  // Parts of each message that are only for screen readers or the Teams UI.
  const NOISE = [
    '[aria-hidden="true"]',
    '[data-tid="message-avatar"]',
    '[data-tid="presence-badge"]',
    '[data-tid="message-actions-menu-hidden-button"]',
    '[data-tid="add-reaction-picker-entry-point-button"]',
    '[data-tid="reactions-summary-item-renderer"]',
  ].join(",");

  // "19/11/2026 9:13 am" from a <time datetime>, or the time as shown.
  function messageTime(time) {
    const shown = time.textContent.trim();
    const when = new Date(time.getAttribute("datetime") || "");
    if (Number.isNaN(when.getTime())) return shown;
    const date = when.toLocaleDateString("en-AU", { day: "2-digit", month: "2-digit", year: "numeric" });
    const clock = when.toLocaleTimeString("en-AU", { hour: "numeric", minute: "2-digit" });
    return `${date} ${clock}`;
  }

  function tidyTeamsChat(root) {
    const doc = root.ownerDocument;

    // The hidden heading on each message repeats its first words and sender.
    for (const h of root.querySelectorAll('[role="heading"]')) {
      const box = h.parentElement;
      if (box && box.querySelector('[data-tid="message-author-name"], [data-tid="chat-pane-message"]')) h.remove();
    }

    // Message text and its images always stay, even when marked hidden.
    for (const el of root.querySelectorAll(NOISE)) {
      if (!el.closest('[id^="content-"]')) el.remove();
    }

    // One "**Sender** date time" line above each message.
    for (const author of root.querySelectorAll('[data-tid="message-author-name"]')) {
      const key = author.id.replace(/^author-/, "");
      const time = key ? root.querySelector(`time[id="timestamp-${key}"]`) : null;
      const line = doc.createElement("p");
      const name = doc.createElement("strong");
      name.textContent = author.textContent.trim();
      line.appendChild(name);
      if (time) {
        line.appendChild(doc.createTextNode(" " + messageTime(time)));
        time.remove();
      }
      author.replaceWith(line);
    }
  }

  globalThis.__qwcTeams = { isTeamsHost, messageTime, tidyTeamsChat };
})();
