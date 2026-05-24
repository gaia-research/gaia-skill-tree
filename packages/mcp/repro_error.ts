
import { z, ZodError } from "zod";
import { formatZodError } from "./src/utils/errors.js";

const schema = z.object({
  username: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9-]*$/, "Invalid GitHub username").max(39),
  type: z.enum(["basic", "extra", "unique", "ultimate"]),
});

try {
  schema.parse({
    username: "invalid_user!",
    type: "invalid_type",
  });
} catch (err) {
  if (err instanceof ZodError) {
    console.log("Formatted Error:");
    console.log(formatZodError(err));
  }
}
