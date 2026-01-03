// Language switcher component

import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

const languages = [
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const changeLanguage = (langCode: string) => {
    i18n.changeLanguage(langCode);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 glass-card rounded-lg text-zinc-400 hover:text-white transition-colors"
        aria-label="Change language"
        aria-expanded={isOpen}
      >
        <Globe className="w-4 h-4" />
        <span className="text-sm">{currentLanguage.flag}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 glass-card rounded-xl shadow-lg border border-white/10 overflow-hidden z-50">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => changeLanguage(lang.code)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                i18n.language === lang.code
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'text-zinc-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className="text-base">{lang.flag}</span>
              <span>{lang.name}</span>
              {i18n.language === lang.code && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-400" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LanguageSwitcher;
