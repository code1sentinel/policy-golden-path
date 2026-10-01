// Validate OSCAL JSON files against an OSCAL JSON schema (used in CI).
// The schema uses Unicode regex classes (\p{L}), so it needs a validator with Unicode regex support: ajv.
//   node scripts/validate_oscal.mjs oscal_catalog_schema.json catalog.json ...
import Ajv from "ajv";
import addFormats from "ajv-formats";
import { readFileSync } from "fs";
const [schemaPath, ...files] = process.argv.slice(2);
const ajv = new Ajv({ allErrors: true, strict: false, unicodeRegExp: true });
addFormats(ajv);
const validate = ajv.compile(JSON.parse(readFileSync(schemaPath, "utf8")));
let bad = 0;
for (const f of files) {
  const ok = validate(JSON.parse(readFileSync(f, "utf8")));
  console.log(ok ? `valid: ${f}` : `INVALID: ${f}`);
  if (!ok) { bad++; for (const e of validate.errors.slice(0, 15)) console.log("  ", e.instancePath, e.message, JSON.stringify(e.params)); }
}
process.exit(bad ? 1 : 0);
