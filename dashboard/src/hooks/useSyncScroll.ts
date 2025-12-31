/**
 * useSyncScroll Hook
 * Synchronizes scrolling between two elements
 */

import { useEffect } from 'react';
import type { RefObject } from 'react';

export function useSyncScroll(
  ref1: RefObject<HTMLElement>,
  ref2: RefObject<HTMLElement>
) {
  useEffect(() => {
    const element1 = ref1.current;
    const element2 = ref2.current;

    if (!element1 || !element2) return;

    let isScrolling1 = false;
    let isScrolling2 = false;

    const handleScroll1 = () => {
      if (isScrolling2) return;
      isScrolling1 = true;

      const scrollPercentage = element1.scrollTop / (element1.scrollHeight - element1.clientHeight);
      element2.scrollTop = scrollPercentage * (element2.scrollHeight - element2.clientHeight);

      setTimeout(() => {
        isScrolling1 = false;
      }, 50);
    };

    const handleScroll2 = () => {
      if (isScrolling1) return;
      isScrolling2 = true;

      const scrollPercentage = element2.scrollTop / (element2.scrollHeight - element2.clientHeight);
      element1.scrollTop = scrollPercentage * (element1.scrollHeight - element1.clientHeight);

      setTimeout(() => {
        isScrolling2 = false;
      }, 50);
    };

    element1.addEventListener('scroll', handleScroll1);
    element2.addEventListener('scroll', handleScroll2);

    return () => {
      element1.removeEventListener('scroll', handleScroll1);
      element2.removeEventListener('scroll', handleScroll2);
    };
  }, [ref1, ref2]);
}
