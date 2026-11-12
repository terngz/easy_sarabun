/* Easy Sarabun Web — file digit-conversion.
 *
 * Self-contained JS port of the conversion logic in file_handler.py and
 * clip_format.py (HTML + RTF + OOXML + XLSX + ODF + plain text), running
 * entirely in the browser via JSZip + DOMParser. Nothing is uploaded.
 *
 * NOTE: This is a NEW web implementation. It does NOT modify or depend on the
 * original Python modules; it reproduces the same transforms in JS.
 */
(function (global) {
  'use strict';
  var EasyEngine = global.EasyEngine;
  var get_converter = EasyEngine.get_converter;

  var THAI_ZERO = EasyEngine.THAI_ZERO;
  var THAI_NINE = EasyEngine.THAI_NINE;

  // ───────────────────────── HTML (from clip_format.py) ─────────────────────────
  // Convert only "text", never tags / attributes / style / entities.
  // Group order: g1 = skip (tags/style/script), g2 = ent (entity), g3 = text
  var _HTML_TOKEN = /(<(?:!--[\s\S]*?--|<style\b[\s\S]*?<\/style\s*>|<script\b[\s\S]*?<\/script\s*>|[^>]*)>)|(&#[xX]?[0-9A-Fa-f]+;|&\w+;)|([^<&]+|[<&])/gi;
  var _NUM_ENTITY = /&#(x?)([0-9a-fA-F]+);/i;

  function convert_html_text(html, reverse) {
    var conv = get_converter(reverse);
    return html.replace(_HTML_TOKEN, function (match, skip, ent, text) {
      if (ent !== undefined) {
        if (reverse) {
          var mm = _NUM_ENTITY.exec(ent);
          if (mm) {
            var code = parseInt(mm[2], mm[1] ? 16 : 10);
            if (code >= THAI_ZERO && code <= THAI_NINE) {
              return String(code - THAI_ZERO);
            }
          }
        }
        return ent;
      }
      return text ? conv(text) : match;
    });
  }

  // ───────────────────────── RTF (from clip_format.py) ─────────────────────────
  var _RTF_TOKEN = /(?:\\u(-?\d+) ?(?:\\'[0-9a-fA-F]{2}|[^\\{}\r\n])?)|(?:\\'([0-9a-fA-F]{2}))|(?:\\\\(?<!\\)([A-Za-z]+)(-?\d+)?( )?)|(?:\\[^A-Za-z])|(\{)|(\})|([^\\{}]+)/gi;
  var _RTF_SKIP = {
    fonttbl: 1, colortbl: 1, stylesheet: 1, info: 1, listtable: 1,
    listoverridetable: 1, rsidtbl: 1, themedata: 1, datastore: 1,
    colorschememapping: 1, latentstyles: 1, pict: 1, object: 1,
    fldinst: 1, generator: 1, bin: 1
  };

  function convert_rtf_bytes(textBytes, reverse) {
    // RTF is byte-oriented; decode as latin-1 to preserve bytes 1:1.
    var rtf = '';
    for (var i = 0; i < textBytes.length; i++) {
      rtf += String.fromCharCode(textBytes[i]);
    }
    var cp874 = rtf.indexOf('\\ansicpg874') !== -1;
    var out = [];
    var stack = [];
    var skip = false;
    var need_delim = false;

    function emit_digit(d) {
      out.push((need_delim ? ' ' : '') + d);
      need_delim = false;
    }

    var re = _RTF_TOKEN;
    re.lastIndex = 0;
    var m;
    while ((m = re.exec(rtf)) !== null) {
      if (m[5] !== undefined) { // open {
        stack.push(skip);
        out.push('{');
        need_delim = false;
      } else if (m[6] !== undefined) { // close }
        skip = stack.length ? stack.pop() : false;
        out.push('}');
        need_delim = false;
      } else if (m[1] !== undefined) { // uni \uN
        var n = parseInt(m[1], 10);
        n = n < 0 ? n + 65536 : n;
        if (reverse && !skip && n >= THAI_ZERO && n <= THAI_NINE) {
          emit_digit(String(n - THAI_ZERO));
        } else {
          out.push(m[0]);
          need_delim = false;
        }
      } else if (m[2] !== undefined) { // hex \'hh
        var h = parseInt(m[2], 16);
        if (reverse && cp874 && !skip && h >= 0xF0 && h <= 0xF9) {
          emit_digit(String(h - 0xF0));
        } else {
          out.push(m[0]);
          need_delim = false;
        }
      } else if (m[3] !== undefined) { // word \foo123
        if (_RTF_SKIP[m[3]]) skip = true;
        out.push(m[0]);
        need_delim = m[4] === undefined;
      } else { // sym \* or text
        if (m[0] === '\\*') skip = true;
        if (m[7] !== undefined && !skip && !reverse) {
          out.push(m[7].replace(/[0-9]/g, function (d) {
            return '\\u' + (THAI_ZERO + parseInt(d, 10)) + '?';
          }));
        } else {
          out.push(m[7] !== undefined ? m[7] : m[0]);
        }
        need_delim = false;
      }
    }

    // Encode back to latin-1 bytes.
    var joined = out.join('');
    var bytes = new Uint8Array(joined.length);
    for (var j = 0; j < joined.length; j++) {
      bytes[j] = joined.charCodeAt(j) & 0xFF;
    }
    return bytes;
  }

  // ───────────────────────── OOXML text nodes (file_handler.py) ─────────────────────────
  // <t> / <a:t> / <m:t> — keep attributes, convert text run.
  var _OOXML_T = new RegExp('(<(?:[\\w.-]+:)?t(?:\\s[^>]*?)?(?<!/)>)([^<]*)(<\\/(?:[\\w.-]+:)?t>)', 'g');

  function convert_ooxml_part(xmlText, reverse) {
    return xmlText.replace(_OOXML_T, function (all, open, inner, close) {
      return open + convert_html_text(inner, reverse) + close;
    });
  }

  // ───────────────────────── Excel cells (file_handler.py) ─────────────────────────
  var _XLSX_CELL = /<c\b([^>]*?)\s*>((?:(?!<\/c>).)*?)<\/c>/g;
  var _XLSX_V = /<v>([^<]*)<\/v>/g;

  function convert_xlsx_sheet(xmlText, reverse) {
    var conv = get_converter(reverse);
    xmlText = convert_ooxml_part(xmlText, reverse);

    return xmlText.replace(_XLSX_CELL, function (cell, attrs, body) {
      var tm = /\bt="([^"]+)"/.exec(attrs);
      if (tm && ['s', 'b', 'd', 'e', 'inlineStr', 'str'].indexOf(tm[1]) !== -1) {
        return cell; // not a numeric cell
      }
      if (body.indexOf('<f') !== -1) {
        return cell; // formula cell — skip
      }
      return '<c' + attrs + '>' + body.replace(_XLSX_V, function (all, v) {
        return '<v>' + conv(v) + '</v>';
      }) + '</c>';
    });
  }

  // ───────────────────────── ODF (file_handler.py, lxml -> DOMParser) ─────────────────────────
  var _ODF_SKIP = {
    date: 1, creator: 1, 'date-string': 1, 'initial-creator': 1,
    'creator-initials': 1, 'binary-data': 1, script: 1,
    'print-date': 1, 'printed-by': 1
  };
  var _ODF_PARTS = { 'content.xml': 1, 'styles.xml': 1 };

  function convert_odf_part(xmlText, reverse) {
    var conv = get_converter(reverse);
    var doc = new DOMParser().parseFromString(xmlText, 'application/xml');
    var walker = doc.createTreeWalker(doc, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i].parentElement;
      if (el && el.tagName) {
        var tag = el.tagName.split(':').pop(); // localname
        if (_ODF_SKIP[tag]) continue;
      }
      if (nodes[i].nodeValue) nodes[i].nodeValue = conv(nodes[i].nodeValue);
    }
    var s = new XMLSerializer().serializeToString(doc);
    // restore leading XML declaration if it existed
    if (/^<\?xml/.test(xmlText) && s.indexOf('<?xml') !== 0) {
      s = '<?xml version="1.0" encoding="UTF-8"?>\n' + s.replace(/^<\?xml[^>]*\?>\s*/, '');
    }
    return s;
  }

  // ───────────────────────── text / html decoding ─────────────────────────
  function decode_text(uint8) {
    // Strip UTF-8 BOM
    if (uint8[0] === 0xEF && uint8[1] === 0xBB && uint8[2] === 0xBF) {
      return { text: new TextDecoder('utf-8').decode(uint8.subarray(3)), enc: 'utf-8' };
    }
    if (uint8[0] === 0xFF && uint8[1] === 0xFE) {
      return { text: new TextDecoder('utf-16le').decode(uint8.subarray(2)), enc: 'utf-16le' };
    }
    if (uint8[0] === 0xFE && uint8[1] === 0xFF) {
      return { text: new TextDecoder('utf-16be').decode(uint8.subarray(2)), enc: 'utf-16be' };
    }
    try {
      return { text: new TextDecoder('utf-8', { fatal: true }).decode(uint8), enc: 'utf-8' };
    } catch (e) {
      // Windows-874 fallback (Thai legacy) — browsers may not support cp874;
      // approximate with cp1252 so byte-preserving output still works.
      var s = '';
      for (var i = 0; i < uint8.length; i++) s += String.fromCharCode(uint8[i]);
      return { text: s, enc: 'latin1' };
    }
  }

  function encode_text(text, enc) {
    if (enc === 'utf-16le') {
      var b16 = new Uint16Array([0xFEFF]);
      var arr = new Uint8Array((text.length + 1) * 2);
      arr.set(new Uint8Array(b16.buffer), 0);
      for (var i = 0; i < text.length; i++) {
        arr[i * 2 + 2] = text.charCodeAt(i) & 0xFF;
        arr[i * 2 + 3] = text.charCodeAt(i) >> 8;
      }
      return arr;
    }
    if (enc === 'latin1') {
      var out = new Uint8Array(text.length);
      for (var j = 0; j < text.length; j++) out[j] = text.charCodeAt(j) & 0xFF;
      return out;
    }
    return new TextEncoder().encode(text);
  }

  // ───────────────────────── zip rewrite (JSZip) ─────────────────────────
  async function transform_zip(file, ext, reverse) {
    var zip = await JSZip.loadAsync(file);
    var outZip = new JSZip();
    var entries = Object.keys(zip.files);
    var prefix = { '.docx': 'word/', '.docm': 'word/', '.pptx': 'ppt/', '.pptm': 'ppt/', '.xlsx': 'xl/', '.xlsm': 'xl/' }[ext] || '';
    var isXlsx = ext === '.xlsx' || ext === '.xlsm';
    var isOdf = ext === '.odt' || ext === '.ods' || ext === '.odp';

    for (var i = 0; i < entries.length; i++) {
      var name = entries[i];
      var entry = zip.files[name];
      var zname = name.replace(/\/$/, '');
      if (entry.dir) {
        outZip.folder(zname);
        continue;
      }
      var data = await entry.async('arraybuffer');
      if (isOdf && _ODF_PARTS[zname]) {
        var odfText = new TextDecoder('utf-8').decode(new Uint8Array(data));
        var odfOut = convert_odf_part(odfText, reverse);
        outZip.file(zname, new Uint8Array(new TextEncoder().encode(odfOut)));
      } else if (isXlsx && /^xl\/worksheets\/[^/]+\.xml$/.test(zname)) {
        var xsText = new TextDecoder('utf-8').decode(new Uint8Array(data));
        var xsOut = convert_xlsx_sheet(xsText, reverse);
        outZip.file(zname, new Uint8Array(new TextEncoder().encode(xsOut)));
      } else if (zname.indexOf(prefix) === 0 && /\.xml$/.test(zname)) {
        var ooText = new TextDecoder('utf-8').decode(new Uint8Array(data));
        var ooOut = convert_ooxml_part(ooText, reverse);
        outZip.file(zname, new Uint8Array(new TextEncoder().encode(ooOut)));
      } else {
        outZip.file(zname, data);
      }
    }
    return outZip.generateAsync({ type: 'uint8array', compression: 'DEFLATE' });
  }

  // ───────────────────────── public API ─────────────────────────
  var EXT_LOOKUP = {
    docx: '.docx', docm: '.docm', pptx: '.pptx', pptm: '.pptm',
    xlsx: '.xlsx', xlsm: '.xlsm', odt: '.odt', ods: '.ods', odp: '.odp',
    rtf: '.rtf', txt: '.txt', md: '.md', csv: '.csv', html: '.html', htm: '.htm'
  };
  var ZIP_EXT = { '.docx': 1, '.docm': 1, '.pptx': 1, '.pptm': 1, '.xlsx': 1, '.xlsm': 1, '.odt': 1, '.ods': 1, '.odp': 1 };

  function is_supported(name) {
    var ext = (name.split('.').pop() || '').toLowerCase();
    return !!EXT_LOOKUP[ext];
  }

  // Returns a Blob of the converted file, or throws.
  async function convert_file(file, reverse) {
    var fname = file.name || 'file';
    var ext = (fname.split('.').pop() || '').toLowerCase();
    var dotExt = EXT_LOOKUP[ext];
    if (!dotExt) {
      throw new Error('ไม่รองรับไฟล์ชนิด .' + (ext || '(ไม่มีนามสกุล)'));
    }
    var buf = await file.arrayBuffer();
    var bytes = new Uint8Array(buf);
    var conv = get_converter(reverse);
    var outBytes;

    if (ZIP_EXT[dotExt]) {
      outBytes = await transform_zip(bytes, dotExt, reverse);
    } else if (dotExt === '.rtf') {
      outBytes = convert_rtf_bytes(bytes, reverse);
    } else {
      // txt / md / csv / html
      var decoded = decode_text(bytes);
      var text = dotExt === '.html' || dotExt === '.htm'
        ? convert_html_text(decoded.text, reverse)
        : conv(decoded.text);
      outBytes = encode_text(text, decoded.enc);
    }

    var stem = fname.replace(/\.[^/.]+$/, '');
    var suffix = reverse ? '_arabic' : '_thai';
    var outName = stem + suffix + dotExt;
    var blob = new Blob([outBytes], { type: 'application/octet-stream' });
    return { blob: blob, name: outName };
  }

  global.EasyWeb = {
    is_supported: is_supported,
    convert_file: convert_file,
    SUPPORTED_EXT: Object.keys(EXT_LOOKUP)
  };
})(window);
