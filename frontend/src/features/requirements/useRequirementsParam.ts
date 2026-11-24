import { useLocation, useNavigate, useSearchParams } from "react-router";
export function useRequirementsParam() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const groupId = params.get("requirements");
  const open = (next = "all") => {
    const p = new URLSearchParams(params);
    p.delete("course");
    p.set("requirements", next);
    const pushed = (location.state as { requirementsModal?: boolean } | null)?.requirementsModal;
    setParams(p, { state: { requirementsModal: groupId ? !!pushed : true }, replace: !!groupId });
  };
  const close = () => {
    if ((location.state as { requirementsModal?: boolean } | null)?.requirementsModal) { navigate(-1); return; }
    const p = new URLSearchParams(params);
    p.delete("requirements");
    setParams(p, { replace: true });
  };
  const openCourse = (code: string) => {
    const p = new URLSearchParams(params);
    p.delete("requirements");
    p.set("course", code);
    setParams(p, { state: { courseDrawer: true } });
  };
  return { groupId, open, close, openCourse, isOpen: groupId !== null && !params.has("course") };
}
