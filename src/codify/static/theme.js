"use strict";

(function () {
  var KEY = "codify:theme";
  var root = document.documentElement;

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function readPref() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (err) { /* private mode */ }
    return "system";
  }

  function apply() {
    var pref = readPref();
    var theme = pref === "system" ? systemTheme() : pref;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-theme-pref", pref);
    root.style.colorScheme = theme;
  }

  function set(pref) {
    try {
      if (pref === "light" || pref === "dark") localStorage.setItem(KEY, pref);
      else localStorage.removeItem(KEY);
    } catch (err) { /* ignore */ }
    apply();
    syncToggle();
  }

  function syncToggle() {
    var pref = readPref();
    var buttons = document.querySelectorAll("[data-theme-choice]");
    for (var i = 0; i < buttons.length; i += 1) {
      var on = buttons[i].getAttribute("data-theme-choice") === pref;
      buttons[i].setAttribute("aria-checked", on ? "true" : "false");
    }
  }

  function bindToggle() {
    var buttons = document.querySelectorAll("[data-theme-choice]");
    for (var i = 0; i < buttons.length; i += 1) {
      (function (button, index) {
        button.addEventListener("click", function () {
          set(button.getAttribute("data-theme-choice"));
        });
        button.addEventListener("keydown", function (event) {
          if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
          event.preventDefault();
          var next = event.key === "ArrowRight"
            ? (index + 1) % buttons.length
            : (index - 1 + buttons.length) % buttons.length;
          buttons[next].focus();
          buttons[next].click();
        });
      })(buttons[i], i);
    }
    syncToggle();
  }

  apply();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
    if (readPref() === "system") apply();
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindToggle);
  } else {
    bindToggle();
  }

  window.codifyTheme = { KEY: KEY, apply: apply, set: set, readPref: readPref };
})();
