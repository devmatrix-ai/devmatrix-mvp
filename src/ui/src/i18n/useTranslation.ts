/**
 * useTranslation - Simple i18n hook for MasterPlan components
 *
 * Provides translation function with support for English and Spanish.
 * Uses browser language detection with fallback to English.
 */

import { useState, useEffect, useCallback } from 'react';
import enTranslations from './en.json';
import esTranslations from './es.json';

/**
 * Supported locale codes
 */
export type LocaleCode = 'en' | 'es';

/**
 * Translation object structure (nested keys)
 */
type Translations = typeof enTranslations;

/**
 * Available translation dictionaries
 */
const translations: Record<LocaleCode, Translations> = {
  en: enTranslations,
  es: esTranslations,
};

/**
 * Detect browser locale and return supported locale code
 */
const detectBrowserLocale = (): LocaleCode => {
  const browserLang = navigator.language.toLowerCase();

  // Check for Spanish variants
  if (browserLang.startsWith('es')) {
    return 'es';
  }

  // Default to English
  return 'en';
};

/**
 * Get value from nested object using dot notation path
 * @example getNestedValue(obj, 'masterplan.phase.discovery')
 */
const getNestedValue = (obj: any, path: string): string | undefined => {
  return path.split('.').reduce((current, key) => {
    return current?.[key];
  }, obj);
};

/**
 * Replace placeholders in translation strings
 * @example replacePlaceholders("Hello {name}", { name: "World" }) => "Hello World"
 */
const replacePlaceholders = (
  template: string,
  values: Record<string, string | number>
): string => {
  return Object.entries(values).reduce((result, [key, value]) => {
    return result.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value));
  }, template);
};

/**
 * Custom hook for translations
 */
export function useTranslation() {
  const [locale, setLocale] = useState<LocaleCode>(detectBrowserLocale());

  // Listen for locale changes (if implementing locale switcher)
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'app_locale' && e.newValue) {
        const newLocale = e.newValue as LocaleCode;
        if (newLocale === 'en' || newLocale === 'es') {
          setLocale(newLocale);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  /**
   * Get translated string for a given key
   * @param key - Translation key in dot notation (e.g., 'masterplan.phase.discovery')
   * @param values - Optional placeholder values (e.g., { seconds: 45 })
   * @returns Translated string or key if translation not found
   */
  const t = useCallback(
    (key: string, values?: Record<string, string | number>): string => {
      const translation = getNestedValue(translations[locale], key);

      if (!translation) {
        console.warn(`Translation missing for key: ${key} (locale: ${locale})`);
        return key;
      }

      if (values) {
        return replacePlaceholders(translation, values);
      }

      return translation;
    },
    [locale]
  );

  /**
   * Change locale programmatically
   */
  const changeLocale = useCallback((newLocale: LocaleCode) => {
    setLocale(newLocale);
    localStorage.setItem('app_locale', newLocale);
  }, []);

  return {
    /** Translation function */
    t,
    /** Current locale code */
    locale,
    /** Change locale programmatically */
    changeLocale,
  };
}

/**
 * Export hook as default
 */
export default useTranslation;
