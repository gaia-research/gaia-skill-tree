import { ZodError } from "zod";

/**
 * Enhances Zod error messages to be more human-readable for AI agents.
 */
export function formatZodError(error: ZodError): string {
  const issues = error.issues.map((issue) => {
    const path = issue.path.join(".");
    let message = issue.message;

    if (issue.code === "invalid_type") {
      message = `Expected ${issue.expected}, but received ${issue.received}`;
    }

    return `* ${path ? `\`${path}\`: ` : ""}${message}`;
  });

  return `Invalid tool input:\n${issues.join("\n")}`;
}

/**
 * Wraps a tool handler to provide better error messages and consistent formatting.
 */
export function withErrorHandling<T>(handler: (args: T) => Promise<string>) {
  return async (args: T) => {
    try {
      const result = await handler(args);
      return { content: [{ type: "text" as const, text: result }] };
    } catch (err) {
      if (err instanceof ZodError) {
        return {
          content: [{ type: "text" as const, text: formatZodError(err) }],
          isError: true,
        };
      }

      const errorMessage = err instanceof Error ? err.message : String(err);
      
      // Check for specific error types to provide better advice
      let helpfulMessage = `Error: ${errorMessage}`;
      if (errorMessage.includes("GITHUB_TOKEN")) {
        helpfulMessage += "\n\nTip: Ensure the GITHUB_TOKEN environment variable is set and has 'repo' permissions.";
      } else if (errorMessage.includes("ENOENT")) {
        helpfulMessage += "\n\nTip: A required file or directory was not found. Check your local registry path.";
      }

      return {
        content: [{ type: "text" as const, text: helpfulMessage }],
        isError: true,
      };
    }
  };
}
