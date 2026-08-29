/* Aditya Taparia — site behaviour.
   Publication filtering, BibTeX toggles, and the video modal.
   No dependencies. */
(function () {
  'use strict';

  /* ------------------------------------------------- publication tabs --- */

  var TABS = { all: 'all', conferences: 'conference', preprints: 'preprint' };

  function activateTab(name, pushHash) {
    var list = document.getElementById('pub-list');
    var buttons = document.querySelectorAll('.tab-button');
    if (!list || !TABS.hasOwnProperty(name)) return;

    list.setAttribute('data-filter', TABS[name]);

    for (var i = 0; i < buttons.length; i++) {
      var isActive = buttons[i].getAttribute('data-tab') === name;
      buttons[i].classList.toggle('active', isActive);
      buttons[i].setAttribute('aria-selected', isActive ? 'true' : 'false');
      buttons[i].setAttribute('tabindex', isActive ? '0' : '-1');
    }

    if (pushHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + name);
    }
  }

  function initTabs() {
    var buttons = document.querySelectorAll('.tab-button');
    if (!buttons.length) return;

    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function (e) {
        e.preventDefault();
        activateTab(this.getAttribute('data-tab'), true);
      });

      // Left/right arrows move between tabs, per the ARIA tabs pattern.
      buttons[i].addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        var all = Array.prototype.slice.call(document.querySelectorAll('.tab-button'));
        var idx = all.indexOf(this);
        var next = e.key === 'ArrowRight'
          ? (idx + 1) % all.length
          : (idx - 1 + all.length) % all.length;
        activateTab(all[next].getAttribute('data-tab'), true);
        all[next].focus();
      });
    }

    function applyHash() {
      var hash = (window.location.hash || '').replace('#', '');
      if (TABS.hasOwnProperty(hash)) activateTab(hash, false);
    }

    // Also handle same-document hash changes, so a pasted #conferences link
    // switches tabs even when the page is already open.
    window.addEventListener('hashchange', applyHash);
    applyHash();
  }

  /* ------------------------------------------------------------ bibtex --- */

  function initBibtex() {
    var toggles = document.querySelectorAll('[data-bibtex-toggle]');
    for (var i = 0; i < toggles.length; i++) {
      toggles[i].addEventListener('click', function (e) {
        e.preventDefault();
        var target = document.getElementById(this.getAttribute('data-bibtex-toggle'));
        if (!target) return;
        var shown = target.classList.toggle('show');
        this.setAttribute('aria-expanded', shown ? 'true' : 'false');
      });
    }
  }

  function initCopy() {
    var buttons = document.querySelectorAll('[data-copy-target]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function (e) {
        e.preventDefault();
        var src = document.getElementById(this.getAttribute('data-copy-target'));
        if (!src || !navigator.clipboard) return;
        var button = this;
        var original = button.getAttribute('data-label') || 'Copy';
        navigator.clipboard.writeText(src.textContent.trim()).then(function () {
          button.innerHTML = '<span class="material-icons">check</span> Copied';
          setTimeout(function () {
            button.innerHTML = '<span class="material-icons">content_copy</span> ' + original;
          }, 1600);
        });
      });
    }
  }

  /* ------------------------------------------------------- video modal --- */

  var lastFocused = null;

  function initModal() {
    var modal = document.getElementById('videoModal');
    var video = document.getElementById('modalVideo');
    if (!modal || !video) return;

    function open(src) {
      lastFocused = document.activeElement;
      video.querySelector('source').src = src;
      video.load();
      modal.classList.add('open');
      var close = modal.querySelector('.close-btn');
      if (close) close.focus();
    }

    function close() {
      video.pause();
      modal.classList.remove('open');
      if (lastFocused && lastFocused.focus) lastFocused.focus();
    }

    var openers = document.querySelectorAll('[data-video]');
    for (var i = 0; i < openers.length; i++) {
      openers[i].addEventListener('click', function (e) {
        e.preventDefault();
        open(this.getAttribute('data-video'));
      });
    }

    var closer = modal.querySelector('.close-btn');
    if (closer) closer.addEventListener('click', close);

    modal.addEventListener('click', function (e) {
      if (e.target === modal) close();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('open')) close();
    });
  }

  function init() {
    initTabs();
    initBibtex();
    initCopy();
    initModal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
