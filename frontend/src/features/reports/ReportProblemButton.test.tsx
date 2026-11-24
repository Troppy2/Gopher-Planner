import { beforeEach, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server, api } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { useSession } from "@/features/auth/session.store";
import { usePlanDraft } from "@/features/plan/plan.store";
import { ReportProblemButton } from "./ReportProblemButton";
import { Modal } from "@/ui/Modal";

const report = { id: 1, targetType: 'course', courseCode: 'TEST 1001', requirementId: null, reason: 'other', note: 'Synthetic note', status: 'open', createdAt: '2026-11-24T12:00:00Z', updatedAt: '2026-11-24T12:00:00Z' };
beforeEach(() => {
  useSession.setState({ signedIn: true });
  server.use(http.get(api('/reports'), () => HttpResponse.json({ reports: [] })));
});

it('requires a reason, sends only contract fields, announces success and remembers the report', async () => {
  let body: unknown;
  server.use(http.post(api('/reports'), async ({ request }) => {
    body = await request.json();
    return HttpResponse.json(report, { status: 201 });
  }));
  const user = userEvent.setup();
  renderWithProviders(<ReportProblemButton target={{ type: 'course', courseCode: 'TEST 1001', title: 'Synthetic introduction' }} />);
  await user.click(screen.getByRole('button', { name: 'Report a problem' }));
  expect(screen.getByRole('dialog')).toHaveTextContent('Synthetic introduction');
  expect(screen.getByRole('button', { name: 'Send report' })).toBeDisabled();
  await user.click(screen.getByLabelText('Something else'));
  await user.type(screen.getByLabelText("What's wrong? (optional)"), 'Synthetic note');
  await user.click(screen.getByRole('button', { name: 'Send report' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(body).toEqual({ targetType: 'course', courseCode: 'TEST 1001', reason: 'other', note: 'Synthetic note' });
  expect(usePlanDraft.getState().announcement).toBe("Thanks. We'll review your report.");
  expect(screen.getByRole('button', { name: 'Reported' })).toBeInTheDocument();
});

it('loads an existing open report and prefills edits', async () => {
  server.use(http.get(api('/reports'), () => HttpResponse.json({ reports: [report] })));
  renderWithProviders(<ReportProblemButton target={{ type: 'course', courseCode: 'TEST 1001' }} />);
  await userEvent.click(await screen.findByRole('button', { name: 'Reported' }));
  expect(screen.getByLabelText('Something else')).toBeChecked();
  expect(screen.getByRole('textbox')).toHaveValue('Synthetic note');
});

for (const status of [429, 503, 0]) {
  it(`preserves input after error ${status}`, async () => {
    server.use(http.post(api('/reports'), () => status ? HttpResponse.json({}, { status }) : HttpResponse.error()));
    const user = userEvent.setup();
    renderWithProviders(<ReportProblemButton target={{ type: 'course', courseCode: 'TEST 1001' }} />);
    await user.click(screen.getByRole('button', { name: 'Report a problem' }));
    await user.click(screen.getByLabelText('Something else'));
    await user.type(screen.getByRole('textbox'), 'Keep this');
    await user.click(screen.getByRole('button', { name: 'Send report' }));
    expect(await screen.findByText(status === 429 ? "You've sent a lot of reports today. Try again tomorrow." : "Couldn't send your report. Check your connection and try again.")).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveValue('Keep this');
    expect(screen.getByLabelText('Something else')).toBeChecked();
  });
}

it('stacks a requirement dialog, keeps expansion, and restores focus on Escape', async () => {
  const user = userEvent.setup();
  renderWithProviders(<Modal open onOpenChange={() => {}} title="Degree requirements" size="lg">
    <details open><summary>Synthetic core</summary><ReportProblemButton target={{ type: 'requirement', requirementId: 'core', label: 'Synthetic core' }} /></details>
  </Modal>);
  const button = screen.getByRole('button', { name: 'Report a problem' });
  await user.click(button);
  expect(document.querySelector('details')).toHaveAttribute('open');
  await user.keyboard('{Escape}');
  expect(screen.getByRole('dialog', { name: 'Degree requirements' })).toBeInTheDocument();
  await waitFor(() => expect(button).toHaveFocus());
});
