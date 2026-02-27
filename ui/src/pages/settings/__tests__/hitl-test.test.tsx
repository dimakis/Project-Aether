import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HITLTestPage from "../hitl-test";

vi.mock("@/api/client", () => ({
  request: vi.fn(),
}));

import { request } from "@/api/client";
const mockRequest = vi.mocked(request);

describe("HITLTestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockRequest.mockResolvedValue({ services: [], count: 0 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders heading and sections", async () => {
    render(<HITLTestPage />);

    expect(screen.getByText("Push Notification HITL")).toBeInTheDocument();
    expect(screen.getByText("Notify Service")).toBeInTheDocument();
    expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    expect(screen.getByText(/Step 2/)).toBeInTheDocument();
  });

  it("discovers notify services on mount using request()", async () => {
    mockRequest.mockResolvedValueOnce({
      services: ["notify.mobile_app_dans_iphone"],
      count: 1,
    });

    render(<HITLTestPage />);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith("/hitl/notify-services");
    });
  });

  it("populates dropdown with discovered services", async () => {
    mockRequest.mockResolvedValueOnce({
      services: ["notify.mobile_app_dans_iphone", "notify.mobile_app_ipad"],
      count: 2,
    });

    render(<HITLTestPage />);

    await waitFor(() => {
      expect(screen.getByText(/dans iphone/)).toBeInTheDocument();
    });
  });

  it("sends test notification via request() with correct path", async () => {
    mockRequest
      .mockResolvedValueOnce({ services: [], count: 0 })
      .mockResolvedValueOnce({
        success: true,
        service: "notify.mobile_app_test",
      });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<HITLTestPage />);

    const input = screen.getByPlaceholderText("notify.mobile_app_your_device");
    await user.type(input, "notify.mobile_app_test");

    const sendButton = screen.getByText("Send Test Notification");
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "/hitl/test-notification",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("notify.mobile_app_test"),
        }),
      );
    });
  });

  it("sends approval notification and starts polling", async () => {
    mockRequest
      .mockResolvedValueOnce({ services: [], count: 0 })
      .mockResolvedValueOnce({
        success: true,
        service: "notify.mobile_app_test",
        test_proposal_id: "abc-123",
      });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<HITLTestPage />);

    const input = screen.getByPlaceholderText("notify.mobile_app_your_device");
    await user.type(input, "notify.mobile_app_test");

    const approvalButton = screen.getByText("Send Approval Notification");
    await user.click(approvalButton);

    await waitFor(() => {
      expect(mockRequest).toHaveBeenCalledWith(
        "/hitl/test-approval",
        expect.objectContaining({ method: "POST" }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Waiting for you to tap/)).toBeInTheDocument();
    });
  });

  it("shows approved status when poll returns action", async () => {
    mockRequest
      .mockResolvedValueOnce({ services: [], count: 0 })
      .mockResolvedValueOnce({
        success: true,
        service: "notify.mobile_app_test",
        test_proposal_id: "abc-123",
      })
      .mockResolvedValueOnce({
        received: true,
        action: "approve",
        status: "success",
        timestamp: Date.now() / 1000,
      });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<HITLTestPage />);

    const input = screen.getByPlaceholderText("notify.mobile_app_your_device");
    await user.type(input, "notify.mobile_app_test");
    await user.click(screen.getByText("Send Approval Notification"));

    // Wait for the approval to be sent
    await waitFor(() => {
      expect(screen.getByText(/Waiting for you to tap/)).toBeInTheDocument();
    });

    // Advance past the first poll interval (2s)
    vi.advanceTimersByTime(2100);

    await waitFor(() => {
      expect(screen.getByText("Approved")).toBeInTheDocument();
    });
  });

  it("shows error result on failure", async () => {
    mockRequest
      .mockResolvedValueOnce({ services: [], count: 0 })
      .mockRejectedValueOnce(new Error("Connection refused"));

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<HITLTestPage />);

    const input = screen.getByPlaceholderText("notify.mobile_app_your_device");
    await user.type(input, "notify.mobile_app_test");

    await user.click(screen.getByText("Send Test Notification"));

    await waitFor(() => {
      expect(screen.getByText("Failed to send")).toBeInTheDocument();
    });
  });
});
