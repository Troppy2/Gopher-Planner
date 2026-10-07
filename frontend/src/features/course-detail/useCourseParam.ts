import { useLocation, useNavigate, useSearchParams } from "react-router";

/** Course details live in `?course=CODE` on whatever screen is open, so the drawer is linkable and Back closes it. */
export function useCourseParam() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const code = params.get("course");

  const open = (next: string) => {
    const p = new URLSearchParams(params);
    p.set("course", next);
    // Only a pushed entry can be closed with Back; a replaced one keeps whatever flag it had.
    const pushed = (location.state as { courseDrawer?: boolean } | null)?.courseDrawer;
    setParams(p, { state: { courseDrawer: code ? !!pushed : true }, replace: !!code });
  };

  const close = () => {
    if ((location.state as { courseDrawer?: boolean } | null)?.courseDrawer) {
      navigate(-1);
      return;
    }
    const p = new URLSearchParams(params);
    p.delete("course");
    setParams(p, { replace: true });
  };

  return { code, open, close };
}
