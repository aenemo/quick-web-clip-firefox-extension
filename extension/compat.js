// Lets the same code run in Firefox (browser.*) and in Chrome or Edge (chrome.*).
// Imported first by the background script and the options page.
const api = globalThis.browser ?? globalThis.chrome;
if (!globalThis.browser) globalThis.browser = api;
if (api && !api.menus && api.contextMenus) api.menus = api.contextMenus;
