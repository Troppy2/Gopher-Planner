import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { GraphCanvas } from "./GraphCanvas";
import { plannedCourse } from "@/test/planning";

beforeEach(() => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
});

it("opens a course on touch tap without capturing scroll gestures", () => {
  const onSelect = vi.fn();
  render(<GraphCanvas courses={[plannedCourse]} terms={[plannedCourse.term!]} selected={null} onSelect={onSelect} reducedMotion />);
  const canvas = screen.getByRole("img");
  const capture = vi.fn();
  Object.assign(canvas, { setPointerCapture: capture });
  const touch = (type: string, y = 0) => {
    const event = new Event(type);
    Object.assign(event, { pointerType: "touch", pointerId: 1, clientX: 0, clientY: y });
    canvas.dispatchEvent(event);
  };
  touch("pointerdown"); touch("pointerup");
  expect(onSelect).toHaveBeenCalledWith(plannedCourse.code);
  onSelect.mockClear();
  touch("pointerdown"); touch("pointermove", 50); touch("pointerup", 50);
  expect(onSelect).not.toHaveBeenCalled();
  touch("pointerdown"); touch("pointercancel"); touch("pointerup");
  expect(onSelect).not.toHaveBeenCalled();
  expect(capture).not.toHaveBeenCalled();
});
afterEach(() => vi.unstubAllGlobals());

it("allows ordinary page scrolling over the graph while retaining explicit zoom gestures", () => {
  render(<GraphCanvas courses={[]} terms={[]} selected={null} onSelect={vi.fn()} reducedMotion />);
  const canvas = screen.getByRole("img");
  const scroll = new WheelEvent("wheel", { deltaY: 200, cancelable: true });
  canvas.dispatchEvent(scroll);
  expect(scroll.defaultPrevented).toBe(false);
  const zoom = new WheelEvent("wheel", { deltaY: -100, ctrlKey: true, cancelable: true });
  canvas.dispatchEvent(zoom);
  expect(zoom.defaultPrevented).toBe(true);
  const capture = vi.fn();
  Object.assign(canvas, { setPointerCapture: capture });
  const touch = new Event("pointerdown");
  Object.defineProperty(touch, "pointerType", { value: "touch" });
  canvas.dispatchEvent(touch);
  expect(capture).not.toHaveBeenCalled();
});
