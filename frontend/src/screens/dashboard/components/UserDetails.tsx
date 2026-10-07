import type { Profile } from "@/api/types";

export function UserDetails({ profile }: { profile?: Profile }) {
  const rows: Array<[string, string]> = [
    ["Major", profile?.major || "Not set"],
    ["Standing", profile?.standing || "Not set"],
    ["Graduation target", profile?.graduationTarget || "Not set"],
    ["Preferred load", profile ? `${profile.creditLoad} credits per term` : "Not set"],
  ];
  return (
    <dl className="kv">
      {rows.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{profile ? v : " "}</dd>
        </div>
      ))}
    </dl>
  );
}
