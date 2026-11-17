/* Small publication enhancements layered on MkDocs Material's native renderer. */
(function () {
  "use strict";
  var toastTimer;
  var commands = [
    {name:"Discover hosts",key:"SUBNET",label:"Subnet",code:"sudo nmap -sn -PR -n $SUBNET -oA hosts-arp",caption:"Find reachable hosts on a local IPv4 segment.",description:"ARP discovery is useful on the local broadcast domain. Confirm scope before sending probes."},
    {name:"Scan services",key:"IP",label:"Target",code:"nmap -sC -sV $IP",caption:"Identify the services behind the open ports.",description:"A service scan is a starting point. Follow the results into the relevant service playbook."},
    {name:"List SMB shares",key:"IP",label:"Target",code:"smbclient -L $IP",caption:"Check which SMB shares are advertised.",description:"Review share visibility and authentication requirements before accessing files."}
  ];
  var defaults = {IP:"10.10.10.10",SUBNET:"10.10.10.0/24"};

  function notify(message) {
    var toast = document.querySelector(".pl-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "pl-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("visible"); }, 2800);
  }

  function copy(text) {
    if (!navigator.clipboard) {
      notify("Select the command text to copy it in this browser.");
      return;
    }
    navigator.clipboard.writeText(text).then(function () { notify("Copied to clipboard"); }, function () {
      notify("Clipboard access is unavailable. Select the command text to copy it.");
    });
  }

  function initializeWorkbench() {
    var root = document.querySelector("[data-runbook-workbench]");
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "true";
    var index = 1;
    var target = root.querySelector("#workbench-target");
    var code = root.querySelector("#example-command");
    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-command]"));
    function state() {
      return window.runbookVariables ? window.runbookVariables.getValues() : {};
    }
    function render(keepInput) {
      var command = commands[index];
      var values = state();
      var value = values[command.key] || defaults[command.key];
      root.querySelector("#target-label").textContent = command.label;
      if (!keepInput) target.value = value;
      target.setAttribute("aria-label", command.label + " for example command");
      root.querySelector("#command-caption").textContent = command.caption;
      root.querySelector("#command-description").textContent = command.description;
      var raw = command.code.replace("$" + command.key, value);
      code.textContent = "";
      var split = raw.indexOf(value);
      code.appendChild(document.createTextNode(raw.slice(0, split)));
      var mark = document.createElement("mark");
      mark.textContent = value;
      code.appendChild(mark);
      code.appendChild(document.createTextNode(raw.slice(split + value.length)));
      tabs.forEach(function (tab, i) {
        tab.setAttribute("aria-selected", String(i === index));
        tab.tabIndex = i === index ? 0 : -1;
      });
      root.querySelector("#command-panel").setAttribute("aria-labelledby", "command-tab-" + index);
    }
    tabs.forEach(function (tab, i) {
      tab.addEventListener("click", function () { index = i; render(false); });
      tab.addEventListener("keydown", function (event) {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].indexOf(event.key) < 0) return;
        event.preventDefault();
        index = event.key === "Home" ? 0 : event.key === "End" ? 2 : (index + (event.key === "ArrowRight" ? 1 : 2)) % 3;
        render(false);
        tabs[index].focus();
      });
    });
    var editing = false;
    target.addEventListener("input", function () {
      editing = true;
      if (window.runbookVariables) {
        var patch = {};
        patch[commands[index].key] = target.value;
        window.runbookVariables.update(patch);
      }
      render(true);
      editing = false;
    });
    root.querySelector("#workbench-copy").addEventListener("click", function () { copy(code.textContent); });
    document.addEventListener("runbook:variables", function () { render(editing); });
    render(false);
  }

  function initializeLibrary() {
    var root = document.querySelector(".library");
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "true";
    var search = root.querySelector("#machine-search");
    var platform = root.querySelector("#platform-filter");
    var difficulty = root.querySelector("#difficulty-filter");
    var count = root.querySelector("#machine-count");
    var cards = Array.prototype.slice.call(root.querySelectorAll(".machine-card"));
    var empty = document.createElement("div");
    empty.className = "empty-state";
    empty.hidden = true;
    var heading = document.createElement("h3");
    heading.textContent = "No matching investigations";
    var paragraph = document.createElement("p");
    paragraph.textContent = "Try a different technique, platform, or difficulty.";
    empty.appendChild(heading);
    empty.appendChild(paragraph);
    root.querySelector("#machine-grid").appendChild(empty);
    var requested = new URL(window.location.href).searchParams.get("platform");
    if (["Active Directory", "Windows", "Linux"].indexOf(requested) >= 0) platform.value = requested;
    function filter() {
      var query = search.value.trim().toLowerCase();
      var visible = 0;
      cards.forEach(function (card) {
        var matches = (platform.value === "All platforms" || card.dataset.platform === platform.value) &&
          (difficulty.value === "Any difficulty" || card.querySelector(".difficulty").textContent === difficulty.value) &&
          card.textContent.toLowerCase().indexOf(query) >= 0;
        card.hidden = !matches;
        if (matches) visible++;
      });
      count.textContent = visible + " of " + cards.length + " investigations";
      empty.hidden = visible !== 0;
    }
    search.addEventListener("input", filter);
    platform.addEventListener("change", filter);
    difficulty.addEventListener("change", filter);
    root.querySelector("#clear-filters").addEventListener("click", function () {
      search.value = ""; platform.value = "All platforms"; difficulty.value = "Any difficulty"; filter();
    });
    filter();
  }

  function imageDialog() {
    var dialog = document.querySelector(".pl-image-dialog");
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.className = "pl-image-dialog";
    dialog.setAttribute("aria-label", "Evidence image");
    var close = document.createElement("button");
    close.type = "button";
    close.className = "icon-button";
    close.textContent = "\u00d7";
    close.setAttribute("aria-label", "Close evidence image");
    close.addEventListener("click", function () { dialog.close(); });
    var image = document.createElement("img");
    var caption = document.createElement("p");
    var original = document.createElement("a");
    original.className = "pl-evidence-original";
    original.textContent = "Open full-size image";
    original.target = "_blank";
    original.rel = "noopener";
    dialog.appendChild(close); dialog.appendChild(image); dialog.appendChild(caption); dialog.appendChild(original);
    dialog.addEventListener("click", function (event) {
      if (event.target !== dialog) return;
      var bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    document.body.appendChild(dialog);
    return dialog;
  }

  function initializeEvidence() {
    document.querySelectorAll(".md-typeset figure img").forEach(function (image) {
      if (image.closest("a, button")) return;
      var button = document.createElement("button");
      button.type = "button";
      button.className = "pl-evidence-button";
      button.setAttribute("aria-label", "Expand evidence: " + (image.alt || "Screenshot"));
      button.dataset.evidence = image.src;
      button.dataset.caption = image.alt || "Evidence screenshot";
      image.parentNode.insertBefore(button, image);
      button.appendChild(image);
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest("button, a");
    if (!target) return;
    if (target.hasAttribute("data-open-search")) {
      var toggle = document.querySelector("#__search");
      if (toggle) {
        toggle.checked = true;
        toggle.dispatchEvent(new Event("change", {bubbles:true}));
        var query = document.querySelector('[data-md-component="search-query"]');
        if (query) query.focus();
      }
    }
    if (target.hasAttribute("data-open-variables")) {
      var opener = document.querySelector("[data-runbook-variables-open]");
      if (opener) opener.click();
    }
    if (target.hasAttribute("data-evidence")) {
      var dialog = imageDialog();
      dialog.querySelector("img").src = target.dataset.evidence;
      dialog.querySelector("img").alt = target.dataset.caption || "Evidence screenshot";
      dialog.querySelector("p").textContent = target.dataset.caption || "";
      dialog.querySelector(".pl-evidence-original").href = dialog.querySelector("img").src;
      dialog.showModal();
    }
  });

  // Use the current rendered text, including engagement substitutions. Keep
  // Material's legacy clipboard handler as a fallback on insecure origins.
  document.addEventListener("click", function (event) {
    var button = event.target.closest('button[data-md-type="copy"]');
    if (!button || !navigator.clipboard) return;
    var pre = button.closest("pre");
    var code = pre && pre.querySelector("code");
    if (!code) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    copy(code.textContent);
  }, true);

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    ["__search", "__drawer"].some(function (id) {
      var toggle = document.getElementById(id);
      if (!toggle || !toggle.checked) return false;
      toggle.checked = false;
      toggle.dispatchEvent(new Event("change", {bubbles:true}));
      var control = document.querySelector('[data-publication-toggle="' + id + '"]');
      if (control) control.focus();
      return true;
    });
  });

  function initializeHeader() {
    document.querySelectorAll('[data-publication-toggle]').forEach(function (control) {
      if (control.dataset.ready) return;
      control.dataset.ready = "true";
      var toggle = document.getElementById(control.dataset.publicationToggle);
      if (!toggle) return;
      function reflect() { control.setAttribute("aria-expanded", String(toggle.checked)); }
      control.addEventListener("click", function () {
        toggle.checked = !toggle.checked;
        toggle.dispatchEvent(new Event("change", {bubbles:true}));
        if (toggle.checked && control.dataset.publicationToggle === "__search") {
          var query = document.querySelector('[data-md-component="search-query"]');
          if (query) query.focus();
        }
      });
      toggle.addEventListener("change", reflect);
      reflect();
    });
  }

  function initialize() { initializeWorkbench(); initializeLibrary(); initializeEvidence(); initializeHeader(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, {once:true});
  else initialize();
  if (typeof document$ !== "undefined") document$.subscribe(initialize);
})();
