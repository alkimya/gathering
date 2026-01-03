// i18n configuration for GatheRing Dashboard

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

i18n
  // Load translations from /public/locales
  .use(Backend)
  // Detect user language
  .use(LanguageDetector)
  // Pass i18n instance to react-i18next
  .use(initReactI18next)
  .init({
    // Fallback language
    fallbackLng: 'en',

    // Supported languages
    supportedLngs: ['en', 'fr'],

    // Debug mode in development
    debug: import.meta.env.DEV,

    // Namespace configuration
    ns: ['common', 'navigation', 'agents', 'circles', 'projects'],
    defaultNS: 'common',

    // Backend options
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },

    // Detection options
    detection: {
      // Order of language detection
      order: ['localStorage', 'navigator', 'htmlTag'],
      // Cache user language
      caches: ['localStorage'],
      // LocalStorage key
      lookupLocalStorage: 'gathering-language',
    },

    // React options
    react: {
      useSuspense: true,
    },

    // Interpolation options
    interpolation: {
      // React already escapes
      escapeValue: false,
    },
  });

export default i18n;
