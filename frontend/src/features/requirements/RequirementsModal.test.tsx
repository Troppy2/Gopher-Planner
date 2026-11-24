import { beforeEach, describe, expect, it } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation, useNavigate } from "react-router";
import { http, HttpResponse } from "msw";
import type { Course, Plan, RequirementProgress } from "@/api/types";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { usePlanDraft } from "@/features/plan/plan.store";
import { UnsavedPlanBar } from "@/features/plan/UnsavedPlanBar";
import { RequirementProgressPanel } from "@/screens/dashboard/components/RequirementProgressPanel";
import { RequirementsModal } from "./RequirementsModal";
const evidence = { matchedCodes: [], missingCodes: [], appliedAdjustments: [] };
const n = (id: string, type: string, parentId: string | null, extra: Partial<RequirementProgress> = {}): RequirementProgress => ({
  id, type, parentId, label: id, category: "Major core", completedStatus: "unsatisfied", projectedStatus: "unsatisfied", completedEvidence: evidence, projectedEvidence: evidence, details: [], ...extra,
});
const c = (code: string, status: Course['status']): Course => ({ code, status, title: `Synthetic ${code}`, credits: 3, term: status === 'plan' ? 'Fall 2027' : null, requirement: 'Major core', offered: ['Fall', 'Spring'], prereqs: [], concurrent: [], professors: [] });
let plan: Plan;
function Location() { const l = useLocation(); const nav = useNavigate(); return <><output data-testid="url">{l.search}</output><button onClick={() => nav(-1)}>Back</button></>; }
function App({ autosave = false }: { autosave?: boolean }) { return <><RequirementProgressPanel plan={plan} /><RequirementsModal />{autosave && <UnsavedPlanBar />}<Location /></>; }
function open(route = '/?requirements=g', autosave = false) { return renderWithProviders(<App autosave={autosave} />, { route }); }
beforeEach(() => {
  usePlanDraft.getState().clear();
  plan = { terms: ['Completed', 'Fall 2026', 'Spring 2027', 'Fall 2027'], currentTerm: 'Fall 2026', baseCredits: 0, catalogTerm: 'Fall 2026', availableCatalogTerms: ['Fall 2026'], warnings: [],
    courses: [c('TEST 1001','done'), c('TEST 1002','prog'), c('TEST 1003','plan'), c('TEST 1004','avail'), c('TEST 1005','block')],
    requirementProgress: [n('g','group',null), n('all','all','g'), n('leaf','course','all',{ label:'TEST 1001' }), n('choice','any','all'), n('branch','course','choice',{ label:'TEST 1002', projectedEvidence:{...evidence, matchedCodes:['TEST 1002']} }), n('other','course','choice',{ label:'TEST 1003' }), n('count','count','all',{ options:['TEST 1004','TEST 1005','TEST 9999'], projectedEvidence:{...evidence,minCourses:2,matchedCourses:0} }), n('credits','credits','all',{ options:['TEST 1004'], projectedEvidence:{...evidence,requiredCredits:9,matchedCredits:3} }), n('review','review','all',{details:['Synthetic advisor note']}), n('met','group',null,{completedStatus:'satisfied',projectedStatus:'satisfied'}), n('track','group',null,{projectedStatus:'satisfied'})] };
  server.use(http.get(api('/programs'),()=>HttpResponse.json({programs:[]})), http.get(api('/plan'),()=>HttpResponse.json(plan)), http.get(api('/profile'),()=>HttpResponse.json({name:'Synthetic',major:'Synthetic B.S.',creditLoad:15,graduationTarget:'Fall 2027'})), http.get(api('/summary'),()=>HttpResponse.json({creditsTotal:120})));
});
describe('requirements modal', () => {
  it('focuses and expands a linked group, renders every rule and course state', async () => {
    open();
    const dialog = within(await screen.findByRole('dialog'));
    const header = await dialog.findByRole('button',{name:/g Major core/});
    await waitFor(()=>expect(header).toHaveFocus());
    expect(header).toHaveAttribute('aria-expanded','true');
    await userEvent.click(dialog.getByRole('button',{name:'Show the other option'}));
    for (const text of ['Complete one option','Choose 2 of these 3','0 of 2 chosen','Earn 9 credits from these courses','3 of 9 credits','Counting toward this','Check this one with your advisor','Synthetic advisor note','Done','In progress','Planned, Fall 2027','Needed','Locked','TEST 9999']) expect(dialog.getAllByText(text).length).toBeGreaterThan(0);
  });
  it('unknown group ids use default expansion without focusing a group', async () => {
    open('/?requirements=stale');
    const d=within(await screen.findByRole('dialog'));
    expect(await d.findByRole('button',{name:/g Major core/})).toHaveAttribute('aria-expanded','true');
    expect(d.getByRole('button',{name:/g Major core/})).not.toHaveFocus();
  });
  it('Still needed hides met and on track groups and placed courses', async () => {
    open(); const d=within(await screen.findByRole('dialog'));
    await d.findByText('Done');
    await userEvent.click(d.getByRole('radio',{name:'Still needed'}));
    for (const text of ['Done','In progress','Planned, Fall 2027']) expect(d.queryByText(text)).not.toBeInTheDocument();
    expect(d.queryByRole('button',{name:/met Major core/})).not.toBeInTheDocument();
    expect(d.queryByRole('button',{name:/track Major core/})).not.toBeInTheDocument();
    expect(d.getAllByText('Needed').length).toBeGreaterThan(0);
  });
  it('adds with targetTerm, announces and immediately shows the draft', async () => {
    open(); const d=within(await screen.findByRole('dialog'));
    await userEvent.click((await d.findAllByRole('button',{name:'Add TEST 1004 to plan'}))[0]);
    expect(usePlanDraft.getState().changes['TEST 1004']).toEqual({status:'plan',term:'Spring 2027'});
    expect(usePlanDraft.getState().announcement).toBe('TEST 1004 added to Spring 2027.');
    expect(d.getAllByText('Planned, Spring 2027').length).toBeGreaterThan(0);
  });
  it('autosaves through the shared bar and refreshes server chips', async () => {
    server.use(http.put(api('/plan'),()=> { plan={...plan,courses:plan.courses.map(x=>x.code==='TEST 1004'?{...x,status:'plan',term:'Spring 2027'}:x),requirementProgress:plan.requirementProgress.map(x=>x.id==='g'?{...x,projectedStatus:'satisfied'}:x)}; return HttpResponse.json(plan); }));
    open('/?requirements=g',true); const d=within(await screen.findByRole('dialog'));
    await userEvent.click((await d.findAllByRole('button',{name:'Add TEST 1004 to plan'}))[0]);
    await waitFor(()=>expect(d.getByRole('button',{name:/g Major core On track/})).toBeInTheDocument(),{timeout:5000});
    expect(usePlanDraft.getState().changes).toEqual({});
  });
  it('opens course details in one navigation when no term fits, and Back restores requirements', async () => {
    plan.courses.find(x=>x.code==='TEST 1004')!.offered=['Summer'];
    open(); const d=within(await screen.findByRole('dialog'));
    await userEvent.click((await d.findAllByRole('button',{name:'Add TEST 1004 to plan'}))[0]);
    expect(screen.getByTestId('url')).toHaveTextContent('?course=TEST+1004');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'Back'}));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });
  it('suppresses Add throughout satisfied ancestors', async () => {
    plan.requirementProgress[1].projectedStatus='satisfied'; open();
    const d=within(await screen.findByRole('dialog')); await d.findByText('Choose 2 of these 3');
    expect(d.queryByRole('button',{name:'Add TEST 1004 to plan'})).not.toBeInTheDocument();
    // Under a met rule, alternatives wait behind a button and read "Also counts", never "Needed".
    await userEvent.click(d.getAllByRole('button',{name:/other courses that count/})[0]);
    expect(d.getAllByText('Also counts').length).toBeGreaterThan(0);
    expect(d.queryByRole('button',{name:'Add TEST 1004 to plan'})).not.toBeInTheDocument();
  });
  it('opens from dashboard rows and See all; closes with Esc, Close and Back', async () => {
    open('/'); await userEvent.click(screen.getByRole('button',{name:/g.*Short/}));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}'); expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'See all requirements'}));
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button',{name:'Close dialog'}));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'See all requirements'}));
    await userEvent.keyboard('{Escape}');
    expect(screen.getByTestId('url')).toBeEmptyDOMElement();
  });
  it('shows catalog selection and unavailable program states', async () => {
    plan.catalogTerm=null; plan.requirementProgress=[]; open();
    expect(await within(await screen.findByRole('dialog')).findByRole('link',{name:'Choose your catalog year'})).toHaveAttribute('href','/flow-chart');
  });
  it('shows unavailable program state', async () => {
    plan.availableCatalogTerms=[]; plan.catalogTerm=null; plan.requirementProgress=[]; open();
    expect(await within(await screen.findByRole('dialog')).findByText("Requirement details aren't available for your major yet.")).toBeInTheDocument();
  });
  it('prioritizes counted and planned courses, truncates and filters large lists', async () => {
    const options=Array.from({length:35},(_,i)=>`TEST ${2000+i}`);
    plan.courses=options.map(code=>c(code,'avail')); plan.courses[34].status='plan'; plan.courses[34].term='Fall 2027';
    plan.requirementProgress=[n('g','group',null), n('list','count','g',{options,projectedEvidence:{...evidence,minCourses:2,matchedCourses:1,matchedCodes:[options[33]]}})];
    open(); const d=within(await screen.findByRole('dialog')); await d.findByText('Choose 2 of these 35');
    expect(d.getAllByRole('link').length).toBe(14);
    await userEvent.click(d.getByRole('button',{name:'Show all 35 courses'})); expect(d.getAllByRole('link').length).toBe(35);
    await userEvent.type(d.getByRole('textbox',{name:'Filter courses'}),'2034'); expect(d.getAllByRole('link').length).toBe(1);
  });
  it('shows loading, error and retry', async () => {
    server.use(http.get(api('/programs'),()=>HttpResponse.json({programs:[]})), http.get(api('/plan'),()=>new HttpResponse(null,{status:500}))); open();
    const d=within(await screen.findByRole('dialog'));
    expect(await d.findByRole('button',{name:'Try again'})).toBeInTheDocument();
    server.use(http.get(api('/programs'),()=>HttpResponse.json({programs:[]})), http.get(api('/plan'),()=>HttpResponse.json(plan)));
    await userEvent.click(d.getByRole('button',{name:'Try again'})); expect(await d.findByText('Done')).toBeInTheDocument();
  });
});



it('uses course evidence codes when an official course label is present', async () => {
  plan.requirementProgress=[n('g','group',null),n('leaf','course','g',{label:'Synthetic official course label',projectedEvidence:{...evidence,missingCodes:['TEST 1004']}})];
  open();
  expect(await within(await screen.findByRole('dialog')).findByRole('link',{name:'TEST 1004'})).toBeInTheDocument();
});
it('renders maximum counts, adjustments, Met markers and server warnings', async () => {
  plan.warnings=['offered_terms_unverified'];
  plan.requirementProgress=[n('g','group',null),n('cap','count','g',{options:['TEST 1004'],projectedStatus:'satisfied',projectedEvidence:{...evidence,maxCourses:1,matchedCourses:0,appliedAdjustments:['synthetic-waiver']},details:['Synthetic waiver applied.']})];
  open(); const d=within(await screen.findByRole('dialog'));
  expect(await d.findByText('Up to 1 of these count')).toBeInTheDocument();
  expect(d.getByText('Adjusted: Synthetic waiver applied.')).toBeInTheDocument();
  expect(d.getByText('Met')).toBeInTheDocument();
  expect(d.getByText(/Some courses don't list which semesters/)).toBeInTheDocument();
});
