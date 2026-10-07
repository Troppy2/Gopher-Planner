import { useEffect, useState } from "react";

/** True after the user scrolls down past `threshold`; false again on any upward scroll or near the top. */
export function useHideOnScroll(threshold = 64) {
  const [hidden, setHidden] = useState(false);
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
