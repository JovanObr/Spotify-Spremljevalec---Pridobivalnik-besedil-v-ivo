import { useCallback, useState } from "react";

/** Languages offered for lyrics translation (names go straight into the AI prompt). */
export const TRANSLATION_LANGUAGES = [
  "Slovenian",
  "English",
  "German",
  "Croatian",
  "Serbian",
  "Italian",
  "French",
  "Spanish",
  "Portuguese",
  "Polish",
  "Czech",
  "Dutch",
  "Swedish",
  "Japanese",
  "Korean",
  "Chinese",
] as const;

const LANGUAGE_KEY = "sc.translation.language";
const ENABLED_KEY = "sc.translation.enabled";

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // storage blocked (private mode, previews)
  }
}

function write(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Not remembered; the setting still works for this visit
  }
}

/** The browser's language if we offer it (and it isn't English), else Slovenian. */
function defaultLanguage(): string {
  try {
    const code = navigator.language.split("-")[0];
    const name = new Intl.DisplayNames(["en"], { type: "language" }).of(code);
    const match = TRANSLATION_LANGUAGES.find((language) => language === name);
    if (match && match !== "English") return match;
  } catch {
    // Old browser: fall through
  }
  return "Slovenian";
}

/** Whether translation is on and into which language; remembered per browser. */
export function useTranslationSettings() {
  const [language, setLanguageState] = useState(() => {
    const saved = read(LANGUAGE_KEY);
    return saved && (TRANSLATION_LANGUAGES as readonly string[]).includes(saved)
      ? saved
      : defaultLanguage();
  });
  const [enabled, setEnabledState] = useState(() => read(ENABLED_KEY) === "1");

  const setLanguage = useCallback((next: string) => {
    setLanguageState(next);
    write(LANGUAGE_KEY, next);
  }, []);

  const setEnabled = useCallback((next: boolean) => {
    setEnabledState(next);
    write(ENABLED_KEY, next ? "1" : "0");
  }, []);

  return { language, enabled, setLanguage, setEnabled };
}
