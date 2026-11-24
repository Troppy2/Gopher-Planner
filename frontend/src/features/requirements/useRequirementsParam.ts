import { useLocation, useNavigate, useSearchParams } from "react-router";

export function useRequirementsParam() {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const groupId = params.get("requirements");
  const open = (id = "all") => {
    const next = new URLSearchParams(params);
    next.delete("course");
    next.set("requirements", id);
    const pushed = (location.state as { requirementsModal?: boolean } | null)?.requirementsModal;
    setParams(next, { state: { requirementsModal: groupId ? !!pushed : true }, replace: !!groupId });
  };
  const close = () => {
    if ((location.state as { requirementsModal?: boolean } | null)?.requirementsModal) {
      navigate(-1);
      return;
    }
    const next = new URLSearchParams(params);
    next.delete("requirements");
    setParams(next, { replace: true });
  };
  return { groupId, open, close };
}
