// ทดสอบ logic ของ worker/index.js โดยจำลอง R2 bucket ในหน่วยความจำ
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// เอาโค้ด Worker มา (แปลง comment ภาษาไทยไม่กระทบ)
const code = readFileSync(fileURLToPath(new URL("./index.js", import.meta.url)), "utf8");

// ผูก env เข้าไปแบบ hardcode เพื่อให้รันใน Node ทดสอบได้
const injected = code.replace(
  /env\.EASY_SARABUN_BUCKET/g,
  "env.EASY_SARABUN_BUCKET"
);

const mod = await import(
  "data:text/javascript;base64," + Buffer.from(injected).toString("base64")
);

// --- Fake R2 bucket ---
const fakeFiles = new Map([
  ["apps/easysarabun/index.html", "<html>index</html>"],
  ["apps/easysarabun/styles.css", "body{}"],
  ["apps/easysarabun/engine.js", "const x=1;"],
  ["apps/easysarabun/app.js", "//app"],
  ["apps/easysarabun/assets/icon.png", "PNG"],
]);
const fakeBucket = {
  async get(key) {
    const v = fakeFiles.get(key);
    if (v === undefined) return null;
    return {
      body: v,
      httpMetadata: { customMetadata: {} },
    };
  },
};
const env = { EASY_SARABUN_BUCKET: fakeBucket };

let pass = 0, fail = 0;
function test(name, got, want) {
  const ok = got === want;
  if (ok) { pass++; console.log("PASS:", name); }
  else { fail++; console.log("FAIL:", name, "| got=" + got, "| want=" + want); }
}

async function hit(path) {
  const req = new Request("https://www.konnextgroup.com" + path);
  const res = await mod.default.fetch(req, env);
  return { status: res.status, ct: res.headers.get("content-type") || "", cc: res.headers.get("cache-control") || "" };
}

// root -> index
let r = await hit("/apps/easysarabun/");
test("root serves index", r.status + "|" + r.ct.startsWith("text/html"), "200|true");

// exact file
r = await hit("/apps/easysarabun/styles.css");
test("serves css with type", r.status + "|" + r.ct.startsWith("text/css"), "200|true");

// without trailing slash (deep / exact file)
r = await hit("/apps/easysarabun/engine.js");
test("serves js", r.status + "|" + r.ct.startsWith("text/javascript"), "200|true");

// asset subpath
r = await hit("/apps/easysarabun/assets/icon.png");
test("serves nested asset", r.status + "|" + r.ct.startsWith("image/png"), "200|true");

// path traversal attempt
r = await hit("/apps/easysarabun/../secrets");
test("path traversal blocked -> fallback index", String(r.status), "200");

// missing file with no extension -> fallback index (SPA)
r = await hit("/apps/easysarabun/faq");
test("deep link fallback index", r.status + "|" + r.ct.startsWith("text/html"), "200|true");

// truly missing -> 404
r = await hit("/apps/easysarabun/does-not-exist.html");
test("missing file 404", String(r.status), "404");

// non-GET
const req = new Request("https://www.konnextgroup.com/apps/easysarabun/", { method: "POST" });
const res = await mod.default.fetch(req, env);
test("POST rejected 405", String(res.status), "405");

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
