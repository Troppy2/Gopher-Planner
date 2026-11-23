import { Link } from "react-router";
import { LegalLayout } from "./LegalLayout";

export default function TermsScreen() {
  return (
    <LegalLayout title="Terms of service">
      <p>
        By signing in to Gopher Planner, you agree to these terms. If you don't agree, please don't use the app.
      </p>

      <h2>What Gopher Planner is</h2>
      <p>
        Gopher Planner is a free, student-built planning tool for University of Minnesota students. It is not an official
        University of Minnesota service and is not endorsed by the University.
      </p>

      <h2>Your plan is a guide, not an audit</h2>
      <p>
        Plans, requirement status, and prerequisite checks are estimates built from catalog data and the information you
        provide. They can be incomplete or out of date. Your APAS report and your academic advisor have the final word on
        your degree requirements, and you are responsible for confirming your courses before you register.
      </p>

      <h2>Who can use it</h2>
      <p>
        You need a University of Minnesota Google account (@umn.edu) to sign in. Use only your own account, and keep the
        information you enter accurate.
      </p>

      <h2>Acceptable use</h2>
      <ul>
        <li>Don't try to access other people's accounts or data.</li>
        <li>Don't upload files that aren't your own academic records.</li>
        <li>Don't overload, probe, or disrupt the service or its data sources.</li>
      </ul>

      <h2>Third-party information</h2>
      <p>
        Course, professor, and grade information may come from or link to outside sources such as the University catalog,
        Rate My Professors, and Gopher Grades. We don't control those sources and can't guarantee their accuracy.
      </p>

      <h2>No warranty</h2>
      <p>
        Gopher Planner is provided as is, without warranties of any kind. We may change, pause, or end the service at any
        time. To the extent the law allows, the project and its contributors aren't liable for decisions made using the app,
        including registration, graduation timing, or financial aid outcomes.
      </p>

      <h2>Your data</h2>
      <p>
        Our <Link to="/privacy">privacy policy</Link> explains what we collect and how to delete it.
      </p>

      <h2>Changes</h2>
      <p>
        We may update these terms. The date at the top shows the latest version. Continuing to use the app after a change
        means you accept the updated terms.
      </p>
    </LegalLayout>
  );
}
