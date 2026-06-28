import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

// Get directories
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MATRIX_PATH = path.join(__dirname, "license-matrix.json");

// Find gaia.json in possible locations
const GAIA_PATHS = [
  path.join(__dirname, "../registry/gaia.json"),
  path.join(__dirname, "../docs/graph/gaia.json"),
  path.join(__dirname, "../.gaia/registry/gaia.json")
];

interface LicenseMatrix {
  compatible_pairs: Record<string, string[]>;
  incompatible_flags: Record<string, string>;
}

function loadMatrix(): LicenseMatrix {
  if (!fs.existsSync(MATRIX_PATH)) {
    console.warn(`[License Matrix] Matrix file not found at ${MATRIX_PATH}. Using default empty matrix.`);
    return { compatible_pairs: {}, incompatible_flags: {} };
  }
  try {
    return JSON.parse(fs.readFileSync(MATRIX_PATH, "utf-8"));
  } catch (err) {
    console.error("Failed to parse license-matrix.json:", err);
    process.exit(1);
  }
}

function loadGaiaJson(): any {
  for (const p of GAIA_PATHS) {
    if (fs.existsSync(p)) {
      try {
        console.log(`[License Validator] Loading gaia.json from ${p}`);
        return JSON.parse(fs.readFileSync(p, "utf-8"));
      } catch (err) {
        console.error(`Failed to parse ${p}:`, err);
      }
    }
  }
  console.error("Could not find a valid gaia.json file.");
  process.exit(1);
}

// Check if two licenses are compatible
function checkCompatibility(
  licA: string,
  licB: string,
  matrix: LicenseMatrix
): { compatible: boolean; reason?: string } {
  const a = licA.trim().toUpperCase();
  const b = licB.trim().toUpperCase();

  if (a === b) return { compatible: true };

  // Check explicit incompatible flags
  const comb1 = `${a} + ${b}`;
  const comb2 = `${b} + ${a}`;

  for (const [key, msg] of Object.entries(matrix.incompatible_flags)) {
    const keyUpper = key.toUpperCase();
    if (keyUpper === comb1 || keyUpper === comb2) {
      return { compatible: false, reason: msg };
    }
    // Handle wildcard match (e.g. CC-BY-NC-*)
    if (keyUpper.endsWith("*")) {
      const prefix = keyUpper.slice(0, -1);
      if (a.startsWith(prefix) || b.startsWith(prefix)) {
        return { compatible: false, reason: msg };
      }
    }
  }

  // Check compatible pairs
  // Normalise matrix keys/values to uppercase for matching
  const checkPair = (key: string, val: string): boolean => {
    const allowed = matrix.compatible_pairs[key] || [];
    return allowed.map(x => x.toUpperCase()).includes(val);
  };

  // Find if either lists the other as compatible
  // If we have explicit keys, check both ways
  const keys = Object.keys(matrix.compatible_pairs).map(k => k.toUpperCase());
  const hasKeyA = keys.includes(a);
  const hasKeyB = keys.includes(b);

  if (hasKeyA || hasKeyB) {
    let allowedBoth = true;
    if (hasKeyA) {
      // Find original case key
      const origKey = Object.keys(matrix.compatible_pairs).find(k => k.toUpperCase() === a)!;
      if (!checkPair(origKey, b)) allowedBoth = false;
    }
    if (hasKeyB && allowedBoth) {
      const origKey = Object.keys(matrix.compatible_pairs).find(k => k.toUpperCase() === b)!;
      if (!checkPair(origKey, a)) allowedBoth = false;
    }
    if (!allowedBoth) {
      return {
        compatible: false,
        reason: `License compatibility not defined or disallowed between ${licA} and ${licB}`
      };
    }
  }

  return { compatible: true };
}

function run() {
  const matrix = loadMatrix();
  const data = loadGaiaJson();
  const skills = data.skills || [];

  console.log(`[License Validator] Starting validation of ${skills.length} skills...`);
  let totalConflicts = 0;

  for (const skill of skills) {
    const collected: Record<string, string> = {};

    const extractLicense = (obj: any): string | null => {
      if (!obj) return null;
      if (typeof obj === "string") return obj;
      if (typeof obj === "object" && obj.license) return obj.license;
      return null;
    };

    // 1. Check direct license field
    if (skill.license) {
      collected["direct"] = skill.license;
    }
    if (skill.licenses) {
      const licList = Array.isArray(skill.licenses) ? skill.licenses : [skill.licenses];
      licList.forEach((lic: any, idx: number) => {
        collected[`licenses[${idx}]`] = String(lic);
      });
    }

    // 2. Check model fields
    if (skill.modelLicense) {
      collected["modelLicense"] = skill.modelLicense;
    } else if (skill.model) {
      const lic = extractLicense(skill.model);
      if (lic) collected["model.license"] = lic;
    }

    // 3. Check adapter fields
    if (skill.adapterLicense) {
      collected["adapterLicense"] = skill.adapterLicense;
    } else if (skill.adapter) {
      const lic = extractLicense(skill.adapter);
      if (lic) collected["adapter.license"] = lic;
    }

    // 4. Check dataset fields
    if (skill.datasetLicense) {
      collected["datasetLicense"] = skill.datasetLicense;
    } else if (skill.dataset) {
      const lic = extractLicense(skill.dataset);
      if (lic) collected["dataset.license"] = lic;
    }

    // 5. Check tool fields
    if (skill.toolLicense) {
      collected["toolLicense"] = skill.toolLicense;
    } else if (skill.tool) {
      const lic = extractLicense(skill.tool);
      if (lic) collected["tool.license"] = lic;
    }

    const licenses = Object.entries(collected);

    if (licenses.length > 1) {
      // Check all pairs
      for (let i = 0; i < licenses.length; i++) {
        for (let j = i + 1; j < licenses.length; j++) {
          const [fieldA, licA] = licenses[i];
          const [fieldB, licB] = licenses[j];

          const check = checkCompatibility(licA, licB, matrix);
          if (!check.compatible) {
            console.error(
              `❌ CONFLICT in skill "${skill.name}" (${skill.id}):` +
              `\n  Field "${fieldA}" has license "${licA}"` +
              `\n  Field "${fieldB}" has license "${licB}"` +
              `\n  Reason: ${check.reason || "Incompatible combinations"}\n`
            );
            totalConflicts++;
          }
        }
      }
    }
  }

  if (totalConflicts > 0) {
    console.error(`[License Validator] FAILED with ${totalConflicts} conflicts detected.`);
    process.exit(1);
  } else {
    console.log(`[License Validator] PASSED. No license conflicts detected.`);
    process.exit(0);
  }
}

run();
