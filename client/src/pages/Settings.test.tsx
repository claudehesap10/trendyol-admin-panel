import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Settings from "./Settings";
import { trpc } from "@/lib/trpc";

// Mock trpc
vi.mock("@/lib/trpc", () => ({
  trpc: {
    trendyol: {
      settings: {
        get: {
          useQuery: vi.fn(),
        },
        update: {
          useMutation: vi.fn(),
        },
      },
    },
  },
}));

// Mock useAuth
vi.mock("@/_core/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: 1, name: "Test User" },
  }),
}));

describe("Settings Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders settings form", () => {
    vi.mocked(trpc.trendyol.settings.get.useQuery).mockReturnValue({
      data: {
        id: 1,
        userId: 1,
        trendyolUrl: "https://www.trendyol.com/sr?mid=1126746&os=1",
        telegramToken: "test-token",
        telegramChatId: "12345",
        smtpServer: "smtp.gmail.com",
        smtpPort: "587",
        smtpEmail: "test@gmail.com",
        smtpPassword: "password",
        recipientEmails: "user1@example.com,user2@example.com",
        cronExpression: "0 * * * *",
        githubToken: "gh-token",
        githubRepo: "owner/repo",
        githubWorkflowId: "workflow.yml",
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(trpc.trendyol.settings.update.useMutation).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    } as any);

    render(<Settings />);

    expect(screen.getByText("Ayarlar")).toBeInTheDocument();
    expect(screen.getByText("Trendyol Mağazası")).toBeInTheDocument();
    expect(screen.getByText("Telegram Bilgileri")).toBeInTheDocument();
    expect(screen.getByText("Email Ayarları")).toBeInTheDocument();
  });

  it("allows adding multiple emails", async () => {
    const user = userEvent.setup();

    vi.mocked(trpc.trendyol.settings.get.useQuery).mockReturnValue({
      data: {
        id: 1,
        userId: 1,
        trendyolUrl: "https://www.trendyol.com",
        telegramToken: "",
        telegramChatId: "",
        smtpServer: "smtp.gmail.com",
        smtpPort: "587",
        smtpEmail: "",
        smtpPassword: "",
        recipientEmails: "",
        cronExpression: "0 * * * *",
        githubToken: "",
        githubRepo: "",
        githubWorkflowId: "",
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(trpc.trendyol.settings.update.useMutation).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    } as any);

    render(<Settings />);

    const emailInput = screen.getByPlaceholderText("alıcı@example.com");
    const addButton = screen.getByRole("button", { name: "" }); // Plus button

    await user.type(emailInput, "test1@example.com");
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText("test1@example.com")).toBeInTheDocument();
    });
  });

  it("shows telegram status", async () => {
    vi.mocked(trpc.trendyol.settings.get.useQuery).mockReturnValue({
      data: {
        id: 1,
        userId: 1,
        trendyolUrl: "https://www.trendyol.com",
        telegramToken: "test-token",
        telegramChatId: "12345",
        smtpServer: "smtp.gmail.com",
        smtpPort: "587",
        smtpEmail: "",
        smtpPassword: "",
        recipientEmails: "",
        cronExpression: "0 * * * *",
        githubToken: "",
        githubRepo: "",
        githubWorkflowId: "",
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(trpc.trendyol.settings.update.useMutation).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    } as any);

    render(<Settings />);

    expect(screen.getByText("Telegram Durumu:")).toBeInTheDocument();
    expect(screen.getByText("Test edilmedi")).toBeInTheDocument();
  });

  it("shows email status", async () => {
    vi.mocked(trpc.trendyol.settings.get.useQuery).mockReturnValue({
      data: {
        id: 1,
        userId: 1,
        trendyolUrl: "https://www.trendyol.com",
        telegramToken: "",
        telegramChatId: "",
        smtpServer: "smtp.gmail.com",
        smtpPort: "587",
        smtpEmail: "test@gmail.com",
        smtpPassword: "password",
        recipientEmails: "user@example.com",
        cronExpression: "0 * * * *",
        githubToken: "",
        githubRepo: "",
        githubWorkflowId: "",
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(trpc.trendyol.settings.update.useMutation).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    } as any);

    render(<Settings />);

    expect(screen.getByText("Email Durumu:")).toBeInTheDocument();
    expect(screen.getByText("Test edilmedi")).toBeInTheDocument();
  });
});
