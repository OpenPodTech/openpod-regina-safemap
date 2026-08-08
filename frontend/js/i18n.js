/**
 * Regina SafeMap — i18n (Internationalization) Module
 * Supports: en, pa, hi, tl, uk, ar, zh
 */
(function () {
  'use strict';

  const SUPPORTED_LANGS = ['en', 'pa', 'hi', 'tl', 'uk', 'ar', 'zh'];
  const STORAGE_KEY = 'safemap_lang';
  let currentStrings = {};
  let currentLang = 'en';

  /**
   * Get translated string by key
   */
  function t(key) {
    return currentStrings[key] || key;
  }

  /**
   * Load language JSON and apply translations
   */
  async function setLanguage(code) {
    if (!SUPPORTED_LANGS.includes(code)) code = 'en';

    try {
      const basePath = document.querySelector('script[src*="i18n.js"]')
        ? ''
        : '';
      // Determine the base path relative to current page
      let jsonPath = 'i18n/' + code + '.json';
      // If we're in a subdirectory (quiz/, report/), adjust path
      if (window.location.pathname.includes('/quiz/') || window.location.pathname.includes('/report/')) {
        jsonPath = '../i18n/' + code + '.json';
      }

      const resp = await fetch(jsonPath);
      if (!resp.ok) throw new Error('Failed to load ' + code);
      currentStrings = await resp.json();
      currentLang = code;
      localStorage.setItem(STORAGE_KEY, code);

      // Apply direction for RTL languages
      if (currentStrings.dir === 'rtl') {
        document.documentElement.setAttribute('dir', 'rtl');
      } else {
        document.documentElement.removeAttribute('dir');
      }

      // Update all elements with data-i18n attribute
      document.querySelectorAll('[data-i18n]').forEach(function (el) {
        const key = el.getAttribute('data-i18n');
        if (currentStrings[key]) {
          el.textContent = currentStrings[key];
        }
      });

      // Update placeholder attributes
      document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
        const key = el.getAttribute('data-i18n-placeholder');
        if (currentStrings[key]) {
          el.setAttribute('placeholder', currentStrings[key]);
        }
      });

      // Dispatch event for other scripts to react
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: code } }));

    } catch (err) {
      console.warn('[i18n] Could not load language:', code, err);
      if (code !== 'en') setLanguage('en');
    }
  }

  /**
   * Get the current language code
   */
  function getCurrentLang() {
    return currentLang;
  }

  /**
   * Initialize — load saved language or default to English
   */
  function init() {
    const saved = localStorage.getItem(STORAGE_KEY);
    const lang = saved && SUPPORTED_LANGS.includes(saved) ? saved : 'en';
    setLanguage(lang);
  }

  // Expose globally
  window.i18n = {
    t: t,
    setLanguage: setLanguage,
    getCurrentLang: getCurrentLang,
    init: init,
    SUPPORTED_LANGS: SUPPORTED_LANGS
  };

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
