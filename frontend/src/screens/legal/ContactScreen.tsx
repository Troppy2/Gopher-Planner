import { ExternalLink } from "lucide-react";
import { ISSUES_URL, LegalLayout, REPO_URL } from "./LegalLayout";

export default function ContactScreen() {
  return (
    <LegalLayout title="Contact" updated={false}>
      <p>Gopher Planner is built and maintained by University of Minnesota students.</p>

      <h2>Report a bug or request a feature</h2>
      <p>
        Open an issue on GitHub. Include what you were doing and what you expected to happen. Don't include your
        transcript, grades, or other personal details in a public issue.
      </p>
      <p>
        <a className="btn" href={ISSUES_URL} target="_blank" rel="noopener noreferrer">
          Open a GitHub issue
          <ExternalLink className="ic sm" aria-hidden />
        </a>
      </p>

      <h2>Privacy or account deletion</h2>
      <p>
        Open a GitHub issue titled "Account request" without any personal details, and a maintainer will follow up to
        verify your @umn.edu account before making changes.
      </p>

      <h2>Questions about your degree</h2>
      <p>
        For questions about your requirements, registration, or graduation, contact your academic advisor or college
        advising office. Gopher Planner can't answer those for the University.
      </p>

      <h2>Source code</h2>
      <p>
        <a href={REPO_URL} target="_blank" rel="noopener noreferrer">
          Gopher Planner on GitHub
        </a>
      </p>
    </LegalLayout>
  );
}
