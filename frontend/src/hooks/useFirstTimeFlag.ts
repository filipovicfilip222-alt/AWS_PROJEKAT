import { useCallback, useEffect, useState } from "react";

/**
 * Returns whether the given key has NOT yet been seen in localStorage,
 * plus a `markSeen` callback to persist the dismissal.
 */
export function useFirstTimeFlag(key: string): {
  isFirstTime: boolean;
  markSeen: () => void;
} {
  const [isFirstTime, setIsFirstTime] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const seen = window.localStorage.getItem(key);
      setIsFirstTime(!seen);
    } catch {
      setIsFirstTime(false);
    }
  }, [key]);

  const markSeen = useCallback(() => {
    setIsFirstTime(false);
    try {
      window.localStorage.setItem(key, "1");
    } catch {
      /* ignore */
    }
  }, [key]);

  return { isFirstTime, markSeen };
}
