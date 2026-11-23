import { useEffect, useRef } from "react";

/**
 * Save `key`'s state shortly after the user stops editing, and once more on unmount if edits are
 * still pending (for example when they leave the page). A state that already failed to save is
 * not retried until it changes, so a rejected save can't loop.
 */
export function useAutosave({ enabled, key, save, failed, delay = 1200 }: {
  enabled: boolean;
  key: string;
  save: () => void;
  failed: boolean;
  delay?: number;
}) {
  const saveRef = useRef(save);
  const pendingRef = useRef(false);
  const failedKey = useRef<string | null>(null);
  useEffect(() => {
    saveRef.current = save;
    pendingRef.current = enabled && key !== failedKey.current;
  });
  useEffect(() => {
    if (failed) failedKey.current = key;
    // Only the failure transition matters; the key at that moment is the one that failed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [failed]);

  useEffect(() => {
    if (!enabled || key === failedKey.current) return;
    const timer = window.setTimeout(() => {
      pendingRef.current = false;
      saveRef.current();
    }, delay);
    return () => window.clearTimeout(timer);
  }, [enabled, key, delay]);

  useEffect(() => () => {
    if (pendingRef.current) saveRef.current();
  }, []);
}
