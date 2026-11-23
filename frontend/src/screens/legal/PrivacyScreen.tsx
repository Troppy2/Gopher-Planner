import { Link } from "react-router";
import { LegalLayout } from "./LegalLayout";

export default function PrivacyScreen() {
  return (
    <LegalLayout title="Privacy policy">
      <p>
        Gopher Planner is a student-built course planner for University of Minnesota students. It is not run by or
        affiliated with the University of Minnesota. This page explains what we collect, why, and what you can do about it.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><b>Your Google account basics:</b> your name, @umn.edu email address, profile picture link, and Google account ID. We use these to sign you in.</li>
        <li><b>Your profile:</b> major, grade standing, career goal, preferred credits per term, and graduation target.</li>
        <li><b>Your coursework:</b> course codes, titles, credits, terms, status, and grades, whether you typed them in or we read them from your APAS report.</li>
        <li><b>Your plan:</b> the courses you planned, the semesters you put them in, and your catalog year.</li>
        <li><b>A sign-in session:</b> a cookie that keeps you signed in for up to 7 days.</li>
      </ul>

      <h2>Your APAS or transcript upload</h2>
      <p>
        When you upload a PDF, we read it to find your courses and liberal education status, then discard the file. We
        keep the file name, the courses we found, and the requirement status. We do not keep the PDF itself, and we do not
        write its contents to our logs.
      </p>

      <h2>How we use it</h2>
      <p>
        Only to run Gopher Planner: signing you in, building and saving your plan, and showing your progress. We do not
        sell your information, show ads, or share your data with other students or advisors.
      </p>

      <h2>Where it is stored</h2>
      <p>
        Your data is stored in a PostgreSQL database hosted by Supabase, and the app runs on a hosted server. Only the
        project maintainers can access these systems.
      </p>

      <h2>Other services</h2>
      <ul>
        <li><b>Google</b> handles sign-in. Google's own privacy policy applies to your Google account.</li>
        <li>
          <b>Rate My Professors and Gopher Grades</b> are linked from course details. We don't send them your data, but
          they have their own privacy practices once you open their sites.
        </li>
      </ul>

      <h2>Cookies</h2>
      <p>
        We use one session cookie to keep you signed in. We don't use advertising or tracking cookies.
      </p>

      <h2>Keeping and deleting your data</h2>
      <p>
        We keep your data while your account exists. You can edit your profile and coursework in Settings at any time. To
        delete your account and everything tied to it, <Link to="/contact">contact us</Link> and we will remove it.
      </p>

      <h2>Changes</h2>
      <p>
        If this policy changes, we'll update the date at the top of this page. Significant changes will also be noted in
        the app.
      </p>
    </LegalLayout>
  );
}
