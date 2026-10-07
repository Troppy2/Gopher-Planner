import { useEffect, useState } from "react";

/**
 * True after the user scrolls down past `threshold`; false again on any upward scroll or near the top.
 * Changing `resetKey` (for example the route) shows the bars again.
 */
export function useHideOnScroll(threshold = 64, resetKey?: unknown) {
  const [hidden, setHidden] = useState(false);
  useEffect(() => setHidden(false), [resetKey]);
  useEffect(() => {
    let last = window.scrollY;
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY;
        const delta = y - last;
        // Ignore tiny jitters so the pill doesn't flicker.
        if (Math.abs(delta) > 4) {
          setHidden(delta > 0 && y > threshold);
          last = y;
        }
        ticking = false;
      });
    };
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, [threshold]);
  return hidden;
}
