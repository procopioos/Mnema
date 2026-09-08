"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";

import { en, type TranslationKey } from "./translations/en";
import { it } from "./translations/it";

export type Language = "en" | "it";

export { type TranslationKey };

const STORAGE_KEY = "mnema.language";
const OLD_STORAGE_KEY = "verity.language";

let languageMigrated = false;
function migrateLegacyLanguage() {
  if (languageMigrated) return;
  languageMigrated = true;
  try {
    if (!localStorage.getItem(STORAGE_KEY) && localStorage.getItem(OLD_STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, localStorage.getItem(OLD_STORAGE_KEY)!);
    }
    localStorage.removeItem(OLD_STORAGE_KEY);
  } catch { /* storage unavailable */ }
}

const DICTIONARIES: Record<Language, Record<TranslationKey, string>> = { en, it };

const LANGUAGE_NAMES: Record<Language, string> = {
  en: "English",
  it: "Italiano",
};

export const LANGUAGES: Language[] = ["en", "it"];

function isLanguage(value: string | null): value is Language {
  return value === "en" || value === "it";
}

const languageListeners = new Set<() => void>();

function subscribeLanguage(listener: () => void) {
  languageListeners.add(listener);
  return () => {
    languageListeners.delete(listener);
  };
}

function readStoredLanguage(): Language {
  try {
    migrateLegacyLanguage();
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLanguage(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

function getLanguageSnapshot(): Language {
  return readStoredLanguage();
}

function getLanguageServerSnapshot(): Language {
  return "en";
}

type LanguageContextValue = {
  language: Language;
  languageName: string;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const language = useSyncExternalStore(subscribeLanguage, getLanguageSnapshot, getLanguageServerSnapshot);

  const t = useCallback((key: TranslationKey) => DICTIONARIES[language][key] ?? key, [language]);

  const setLanguage = useCallback((lang: Language) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // storage unavailable; still apply for this session
    }
    document.documentElement.lang = lang;
    languageListeners.forEach((listener) => listener());
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({ language, languageName: LANGUAGE_NAMES[language], setLanguage, t }),
    [language, setLanguage, t],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}