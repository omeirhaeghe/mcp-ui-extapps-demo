// Tiny MCP-UI host SDK — emits the spec postMessage shapes.
// Same wire protocol works whether the iframe is loaded via srcdoc (inline)
// or src (text/uri-list / resource_link).
(function (global) {
  function send(type, payload) {
    parent.postMessage({ type: type, payload: payload || {} }, "*");
  }
  global.mcpUI = {
    callTool:   function (toolName, params) { send("tool", { toolName: toolName, params: params || {} }); },
    sendPrompt: function (prompt)            { send("prompt", { prompt: prompt }); },
    openLink:   function (url)               { send("link", { url: url }); },
    notify:     function (message)           { send("notify", { message: message }); },
    setHeight:  function (height)            { send("size", { height: Math.round(height) }); },
    autoSize:   function () {
      var sync = function () {
        global.mcpUI.setHeight(document.body.scrollHeight + 8);
      };
      requestAnimationFrame(sync);
      var ro = new ResizeObserver(sync);
      ro.observe(document.body);
    },
  };
})(window);
