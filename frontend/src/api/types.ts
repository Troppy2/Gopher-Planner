export type CourseStatus = "done" | "prog" | "plan" | "avail" | "block";
export type Season = "Fall" | "Spring" | "Summer";
export type Requirement = "Major core" | "Math and stats" | "Elective" | "Liberal ed";

/** A term label such as "Fall 2026". "Completed" groups everything already finished. */
export type TermId = string;

export interface Course {
  code: string;
  title: string;
  credits: number;
  status: CourseStatus;
  requirement: Requirement;
  offered: Season[];
  prereqs: string[];
  concurrent: string[];
  professors: string[];
  term: TermId | null;
  lockReason?: string;
}

export interface Summary {
  gpa: number | null;
  gradedCredits: number;
  creditsCompleted: number;
  creditsTotal: number;
  percentComplete: number | null;
  program: string;
  source: string;
}

export interface Profile {
  name: string;
  major: string;
  standing: string;
  careerGoals: string;
  creditLoad: number;
  graduationTarget: string;
  onboarded: boolean;
}

export interface Plan {
  /** Ordered: "Completed", current term, then every future term. */
  terms: TermId[];
  currentTerm: TermId;
  /** Credits earned before any course listed here (transfer, AP, older terms). */
  baseCredits: number;
  courses: Course[];
}

export interface PlanChange {
  code: string;
  status: CourseStatus;
  term: TermId | null;
}

export interface Options {
  majors: string[];
  standings: string[];
  graduationTargets: string[];
  subjects: string[];
  /** Career paths offered per major. */
  careers: Record<string, string[]>;
}

export interface CourseFilters {
  q?: string;
  subject?: string;
  level?: string;
  credits?: string;
  term?: string;
  requirement?: string;
  availability?: string;
}

export type TranscriptStatus = "parsing" | "parsed" | "no_text" | "failed";

export interface Transcript {
  id: string;
  fileName: string;
  status: TranscriptStatus;
  completed: number;
  inProgress: number;
}
