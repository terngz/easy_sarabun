/* Easy Sarabun Web — quick Node sanity test.
 * Verifies the engine + text/HTML conversion logic. Run: node test.js
 * This is a test harness only (not part of the web app).
 */
'use strict';

// Minimal browser shims so web.js can load unchanged in Node.
global.window = {};
global.DOMParser = class {
  parseFromString() { throw new Error('ODF/XML test not run in Node (needs DOMParser)'); }
};
global.XMLSerializer = class { serializeToString(d) { return d; } };
global.NodeFilter = { SHOW_TEXT: 4 };

require('./engine.js');
require('./web.js');

let pass = 0, fail = 0;
function assert(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? ' — ' + extra : '')); }
}

const E = window.EasyEngine;
console.log('engine.js');
assert('to_thai converts arabic digits', E.to_thai('Price 1234 baht') === 'Price ๑๒๓๔ baht');
assert('to_arabic converts thai digits', E.to_arabic('ราคา ๑๒๓๔ บาท') === 'ราคา 1234 บาท');
assert('to_thai empty string', E.to_thai('') === '');
assert('get_converter default = to_thai', E.get_converter(false)('5678') === '๕๖๗๘');
assert('get_converter reverse = to_arabic', E.get_converter(true)('๕๖๗๘') === '5678');

const W = window.EasyWeb;
console.log('web.js — API surface');
assert('is_supported docx', W.is_supported('a.docx'));
assert('is_supported rtf', W.is_supported('a.rtf'));
assert('reject exe', W.is_supported('a.exe') === false);
assert('supported list non-empty', W.SUPPORTED_EXT.length > 5);

console.log('web.js — plain text conversion');
let out, name;
(async function () {
  const bytes = new TextEncoder().encode('ค่า 1234 บาท 5678\n');
  const file = {
    name: 'test.txt',
    async arrayBuffer() { return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength); }
  };
  try {
    const res = await W.convert_file(file, false);
    out = new TextDecoder('utf-8').decode(await res.blob.arrayBuffer());
    name = res.name;
    assert('txt arabic->thai', out === 'ค่า ๑๒๓๔ บาท ๕๖๗๘\n', 'got: ' + JSON.stringify(out));
    assert('txt output name _thai', name === 'test_thai.txt', 'got: ' + name);
  } catch (e) {
    fail++;
    console.log('  ✗ txt conversion threw: ' + e.message);
  }

  // Reverse direction: thai -> arabic
  try {
    const bytesAr = new TextEncoder().encode('ยอด ๕๖๗๘ บาท');
    const fileAr = { name: 'b.txt', async arrayBuffer() { return bytesAr.buffer.slice(bytesAr.byteOffset, bytesAr.byteOffset + bytesAr.byteLength); } };
    const resAr = await W.convert_file(fileAr, true);
    const outAr = new TextDecoder('utf-8').decode(await resAr.blob.arrayBuffer());
    assert('txt thai->arabic', outAr === 'ยอด 5678 บาท', 'got: ' + JSON.stringify(outAr));
    assert('txt reverse output name _arabic', resAr.name === 'b_arabic.txt');
  } catch (e) {
    fail++;
    console.log('  ✗ txt reverse threw: ' + e.message);
  }

  console.log('\nResult: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
